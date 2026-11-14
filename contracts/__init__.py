"""Versioned contracts between the hive engine and a future UI.

Version 1 is the shape Timofey's frontend can code against before the
FastAPI process exists. The current Streamlit app does not emit these
events yet.
"""

from contracts.v1 import CONTRACT_VERSION

__all__ = ["CONTRACT_VERSION"]
