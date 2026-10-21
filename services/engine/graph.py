"""One bounded async graph for both selection methods; no duplicate runtime loop."""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class LoopState(TypedDict):
    done: bool


def build_graph(execution):
    async def step(_state):
        return {"done": await execution.step()}

    graph = StateGraph(LoopState)
    graph.add_node("bounded_turn", step)
    graph.add_edge(START, "bounded_turn")
    graph.add_conditional_edges(
        "bounded_turn", lambda state: state["done"], {True: END, False: "bounded_turn"}
    )
    return graph.compile()
