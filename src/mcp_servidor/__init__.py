"""Servidor MCP do AZ1.

O pacote se chama `mcp_servidor`, e não `mcp`, porque `src/` está no caminho de
importação: um `src/mcp/` sombrearia o pacote `mcp` do qual o `fastmcp` depende.
"""

from mcp_servidor.servidor import aplicativo_asgi, mcp, responder_consulta

__all__ = ["aplicativo_asgi", "mcp", "responder_consulta"]
