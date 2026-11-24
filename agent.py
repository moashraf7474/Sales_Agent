"""
Sales Insights Agent
--------------------
An agent that analyzes a sales file (CSV/Excel) using OpenRouter + function calling.

The whole idea is the loop in Agent.run():
  1. Send the question + tool definitions to the model
  2. The model asks for a tool (function_call)
  3. We execute it and send back the result (function_response)
  4. Repeat until the model gives a final answer (no function_call)
"""

import contextlib
import io
import json
import os
import traceback

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from openai import OpenAI

# The model can be changed via an environment variable.
MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")
MAX_STEPS = 12  # hard limit on steps so the agent can't loop forever
MAX_TOOL_OUTPUT = 4000  # truncate long tool output so we don't waste tokens

SYSTEM_PROMPT = """You are an expert sales data analyst.
You have a DataFrame called df containing sales data. Your job:
- Always start with inspect_data to understand the columns (names may be in any language).
- Use run_python to compute things. Write pandas code and use print() to see the result.
- If the code returns an error, read the error, fix it, and try again.
- To show a chart: build it with plotly express (px) and call show_chart(fig, "title") inside the code.
- To show a key number on the dashboard: call add_kpi(label, value).
- Never make up numbers: every number you state must come from the code.
- Final answer: a short summary with the key insights and practical recommendations (e.g. a promotion on a stagnant product).
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "inspect_data",
            "description": "Returns the column names, types, the first 5 rows, and the row count. Use it first.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": (
                "Executes Python code on the DataFrame named df. Available: pd, px, go, df, "
                "show_chart(fig, title), add_kpi(label, value). "
                "Use print() to see results."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python code"},
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_kpi",
            "description": "Adds a key-number card to the dashboard (e.g. total revenue).",
            "parameters": {
                "type": "object",
                "properties": {
                    "label": {"type": "string", "description": "Name of the number"},
                    "value": {"type": "string", "description": "The formatted value"},
                },
                "required": ["label", "value"],
            },
        },
    },
]


class Agent:
    def __init__(self, df: pd.DataFrame, api_key: str | None = None):
        self.df = df
        self.charts: list[tuple[str, go.Figure]] = []
        self.kpis: list[tuple[str, str]] = []
        key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not key:
            raise ValueError("An OpenRouter API key is required.")
        self.client = OpenAI(
            api_key=key,
            base_url="https://openrouter.ai/api/v1",
        )
        self.history: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]  # memory: remembers previous questions

    # ---------------- Tools ----------------
    def inspect_data(self) -> str:
        buf = io.StringIO()
        self.df.info(buf=buf)
        return f"{buf.getvalue()}\n\nFirst 5 rows:\n{self.df.head().to_string()}"

    def add_kpi(self, label: str, value: str) -> str:
        self.kpis.append((str(label), str(value)))
        return f"Card added: {label} = {value}"

    def run_python(self, code: str) -> str:
        def show_chart(fig, title: str = ""):
            if title:
                fig.update_layout(title=title)
            self.charts.append((title, fig))
            print(f"[Chart drawn: {title}]")

        env = {
            "df": self.df.copy(),  # a copy so the code can't corrupt the original
            "pd": pd,
            "px": px,
            "go": go,
            "show_chart": show_chart,
            "add_kpi": self.add_kpi,
        }
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                exec(code, env)  # ⚠️ for local use only, not for public deployment
            result = out.getvalue() or "(The code ran with no output. Use print() if you want to see a result)"
        except Exception as e:
            # Put the error type first so the model sees it even if the traceback is long
            result = f"ERROR: {type(e).__name__}: {e}\n\n{traceback.format_exc(limit=-2)}"
        return result[:MAX_TOOL_OUTPUT]

    def _call_tool(self, name: str, args: dict) -> str:
        if name == "inspect_data":
            return self.inspect_data()
        if name == "run_python":
            return self.run_python(args.get("code", ""))
        if name == "add_kpi":
            return self.add_kpi(args.get("label", ""), args.get("value", ""))
        return f"ERROR: unknown tool {name}"

    # ---------------- The Agent Loop ----------------
    def run(self, question: str, on_step=None) -> str:
        """Runs the loop and returns the final answer. on_step(kind, text) shows the steps in the UI."""
        step = on_step or (lambda kind, text: None)
        self.history.append({"role": "user", "content": question})

        for i in range(MAX_STEPS):
            response = self.client.chat.completions.create(
                model=MODEL,
                messages=self.history,
                tools=TOOLS,
                tool_choice="auto",
            )
            message = response.choices[0].message
            calls = message.tool_calls or []
            if not calls:  # no tool requested = this is the final answer
                final_answer = message.content or "(The model returned no answer)"
                self.history.append({"role": "assistant", "content": final_answer})
                return final_answer

            assistant_message = {"role": "assistant", "content": message.content, "tool_calls": []}
            for call in calls:
                assistant_message["tool_calls"].append(
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                )
            self.history.append(assistant_message)

            for call in calls:
                name = call.function.name
                try:
                    args = json.loads(call.function.arguments or "{}")
                except json.JSONDecodeError as e:
                    args = {}
                    result = f"ERROR: Invalid JSON tool arguments: {e}"
                else:
                    result = self._call_tool(name, args)
                step("tool", f"🔧 {name}\n{args.get('code', args) if name == 'run_python' else args}")
                step("result", result)
                self.history.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "name": name,
                        "content": result,
                    }
                )

        return "Reached the maximum number of steps. Try a simpler or clearer question."
