"""Example: Using OpenAgent SDK REST API Server."""

from openagent import OpenAgentEngine, SQLiteStorage, run_server


def main():
    print("=" * 60)
    print("OpenAgent SDK - REST API Server Example")
    print("=" * 60)
    
    # Initialize with SQLite storage
    print("\n1. Initializing agent state with SQLite storage...")
    storage = SQLiteStorage(db_path="./api_example.db")
    engine = OpenAgentEngine(storage=storage)
    
    # Create a sample plan
    print("\n2. Creating a sample task plan...")
    engine.create_plan(
        goal="Build a REST API for task management",
        phases=["Design", "Implement", "Test", "Deploy"]
    )
    print("   Plan created successfully!")
    
    # Add a note
    print("\n3. Adding a note...")
    engine.add_note("Use FastAPI for the REST API", section="Design")
    print("   Note added!")
    
    # Add a decision
    print("\n4. Recording a decision...")
    engine.add_decision(
        decision="Use Pydantic for validation",
        reason="Type safety and automatic API documentation"
    )
    print("   Decision recorded!")
    
    print("\n" + "=" * 60)
    print("Starting REST API Server...")
    print("=" * 60)
    
    # Start the REST API server
    run_server(
        host="localhost",
        port=8080,
        workspace=".",
    )


if __name__ == "__main__":
    main()
