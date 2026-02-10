import asyncio
import os
import sys

# Ensure current directory is in path
sys.path.append(os.getcwd())

try:
    from app.services.agent_graph import agent_service
except ImportError as e:
    print(f"Error importing agent_service: {e}")
    sys.exit(1)

async def main():
    print("Generating graph visualization...")
    
    # Create output directory
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    graph = agent_service.get_graph()
    
    # 1. Save Mermaid Syntax
    try:
        mermaid_syntax = graph.get_graph().draw_mermaid()
        mmd_path = os.path.join(output_dir, "graph.mmd")
        with open(mmd_path, "w", encoding="utf-8") as f:
            f.write(mermaid_syntax)
        print(f"Graph Mermaid syntax saved to {mmd_path}")
    except Exception as e:
        print(f"Failed to generate Mermaid syntax: {e}")

    # 2. Save PNG Image
    try:
        # Requires extra dependencies (grandalf or similar)
        png_data = graph.get_graph().draw_mermaid_png()
        png_path = os.path.join(output_dir, "graph.png")
        with open(png_path, "wb") as f:
            f.write(png_data)
        print(f"Graph Image saved to {png_path}")
    except Exception as e:
        print(f"Failed to generate PNG image (dependencies missing?): {e}")

if __name__ == "__main__":
    asyncio.run(main())
