"""Basic example of using OpenAgent SDK."""

import json
from openagent import OpenAgentEngine


def main():
    print("=" * 60)
    print("OpenAgent SDK - Basic Example")
    print("=" * 60)
    
    # Initialize the engine with a workspace
    engine = OpenAgentEngine()
    
    # Create a task plan
    print("\n1. Creating a task plan...")
    plan = engine.create_plan(
        goal="Build a REST API for task management",
        phases=["Design", "Implement", "Test", "Deploy"]
    )
    print(json.dumps(plan, indent=2))
    
    # Start the first phase
    print("\n2. Starting first phase...")
    result = engine.start_phase("Design")
    print(json.dumps(result, indent=2))
    
    # Add some notes
    print("\n3. Adding notes...")
    engine.add_note(
        content="Use FastAPI for the REST API framework",
        section="Design"
    )
    engine.add_note(
        content="Use PostgreSQL for database",
        section="Design"
    )
    print("Notes added!")
    
    # Add a decision
    print("\n4. Recording a decision...")
    engine.add_decision(
        decision="Use JWT for authentication",
        rationale="JWT is stateless and scales better than session-based auth"
    )
    print("Decision recorded!")
    
    # Complete a phase
    print("\n5. Completing 'Design' phase...")
    result = engine.complete_phase("Design")
    print(json.dumps(result, indent=2))
    
    # Get current status
    print("\n6. Getting current status...")
    status = engine.get_status()
    print(json.dumps(status, indent=2))
    
    # Add an error (for demonstration)
    print("\n7. Logging an error...")
    engine.log_error(
        error="Database connection timeout",
        resolution="Increased connection pool size and added retry logic"
    )
    print("Error logged!")
    
    # Get all notes
    print("\n8. Getting all notes...")
    notes = engine.get_notes()
    print(json.dumps(notes, indent=2))
    
    # Get all decisions
    print("\n9. Getting all decisions...")
    decisions = engine.get_decisions()
    print(json.dumps(decisions, indent=2))
    
    # Get all errors
    print("\n10. Getting all errors...")
    errors = engine.get_errors()
    print(json.dumps(errors, indent=2))
    
    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
