"""
Agentic Controller: LLM-driven UAV swarm control with feedback loop.
Integrates Gemini API with simulation through translation layer.
"""

import os
import json
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import google.generativeai as genai

from translation_schema import MissionPlan, ACTION_TEMPLATES, LLM_SYSTEM_PROMPT
from api_translator import SimulationAPIClient, EnvironmentTranslator


class AgenticSwarmController:
    """
    Main controller for LLM-driven swarm operations.
    Handles natural language → structured actions → API execution → feedback.
    """

    def __init__(self, api_base_url: str = "http://localhost:8000", gemini_model: str = "gemini-2.0-flash-exp"):
        """
        Initialize the agentic controller.

        Args:
            api_base_url: Base URL of simulation API
            gemini_model: Gemini model to use for generation
        """
        # Load environment variables
        load_dotenv(dotenv_path="../.env")
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in .env file")

        # Configure Gemini
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(gemini_model)

        # Initialize API client and translator
        self.api_client = SimulationAPIClient(api_base_url)
        self.env_translator = EnvironmentTranslator()

        # Build system prompt with action templates
        templates_json = json.dumps(ACTION_TEMPLATES, indent=2)
        self.system_prompt = LLM_SYSTEM_PROMPT.format(action_templates=templates_json)

        print("[Controller] Initialized")
        print(f"[Controller] Using model: {gemini_model}")
        print(f"[Controller] API endpoint: {api_base_url}")

        # Check API health
        if not self.api_client.health_check():
            print("[Controller] ⚠ Warning: Simulation API not responding")
            print("[Controller] Make sure simulation is running: python main.py")

    def process_command(self, user_command: str, execute: bool = True) -> Dict[str, Any]:
        """
        Process a natural language command through the full pipeline.

        Args:
            user_command: Natural language instruction
            execute: Whether to execute the plan (False for dry-run)

        Returns:
            Dict containing plan, execution results, and feedback
        """
        print(f"\n{'='*70}")
        print(f"[Controller] Processing Command:")
        print(f"[Controller] \"{user_command}\"")
        print(f"{'='*70}\n")

        # Step 1: Get current state
        print("[Controller] Step 1: Fetching current swarm state...")
        current_state = self.api_client.get_state()
        state_summary = self.env_translator.state_to_summary(current_state) if current_state else "Unknown state"
        print(f"[Controller] Current State: {state_summary}")

        # Step 2: Generate structured plan from LLM
        print("\n[Controller] Step 2: Generating mission plan with LLM...")
        try:
            mission_plan = self._generate_plan(user_command, current_state)
            print(f"[Controller] ✓ Plan generated: {mission_plan.mission_name}")
            print(f"[Controller] Actions: {len(mission_plan.actions)}")
        except Exception as e:
            error_msg = f"Failed to generate plan: {str(e)}"
            print(f"[Controller] ✗ Error: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "command": user_command
            }

        # Step 3: Display plan
        print("\n[Controller] Step 3: Mission Plan:")
        print(f"{'─'*70}")
        for idx, action in enumerate(mission_plan.actions, 1):
            print(f"  {idx}. {action.action_type.upper()} → Drones {action.drone_ids}")
            print(f"     Parameters: {action.parameters}")
            print(f"     Priority: {action.priority}, Wait: {action.wait_for_completion}")
        print(f"{'─'*70}")

        # Step 4: Execute if requested
        execution_result = None
        if execute:
            print("\n[Controller] Step 4: Executing mission...")
            execution_result = self.api_client.execute_mission(
                mission_plan,
                feedback_callback=self._log_feedback
            )
        else:
            print("\n[Controller] Step 4: Skipping execution (dry-run mode)")

        # Step 5: Get final state and generate summary
        print("\n[Controller] Step 5: Gathering results...")
        final_state = self.api_client.get_state()
        final_summary = self.env_translator.state_to_text(final_state) if final_state else "No final state"

        result = {
            "success": True,
            "command": user_command,
            "initial_state": current_state,
            "mission_plan": mission_plan.dict(),
            "execution_result": execution_result,
            "final_state": final_state,
            "final_summary": final_summary
        }

        print(f"\n{'='*70}")
        print("[Controller] Command Processing Complete")
        print(f"{'='*70}\n")

        return result

    def _generate_plan(self, user_command: str, current_state: Optional[Dict]) -> MissionPlan:
        """
        Use LLM to generate structured mission plan from natural language.

        Args:
            user_command: User's natural language instruction
            current_state: Current simulation state for context

        Returns:
            Validated MissionPlan object
        """
        # Build prompt with context
        state_context = ""
        if current_state:
            state_context = f"\nCurrent Swarm State:\n{self.env_translator.state_to_text(current_state)}\n"

        full_prompt = f"""{self.system_prompt}

{state_context}

User Command: "{user_command}"

Generate a MissionPlan in valid JSON format:"""

        # Call LLM
        response = self.model.generate_content(full_prompt)
        response_text = response.text

        # Extract JSON from response (handle markdown code blocks)
        json_text = self._extract_json(response_text)

        # Parse and validate
        try:
            plan_dict = json.loads(json_text)
            mission_plan = MissionPlan(**plan_dict)
            return mission_plan
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON from LLM: {e}\nResponse: {json_text}")
        except Exception as e:
            raise ValueError(f"Invalid mission plan format: {e}\nData: {plan_dict}")

    def _extract_json(self, text: str) -> str:
        """Extract JSON from LLM response, handling markdown code blocks."""
        # Remove markdown code blocks if present
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        return text.strip()

    def _log_feedback(self, action, result, state):
        """Callback for logging feedback during mission execution."""
        if state:
            summary = self.env_translator.state_to_summary(state)
            print(f"[Feedback] After {action.action_type}: {summary}")

    def interactive_mode(self):
        """
        Run interactive command loop for testing.
        """
        print("\n" + "="*70)
        print("  Agentic Swarm Controller - Interactive Mode")
        print("="*70)
        print("\nCommands:")
        print("  - Enter natural language commands to control the swarm")
        print("  - Type 'state' to see current drone states")
        print("  - Type 'dry' + command for dry-run (no execution)")
        print("  - Type 'quit' or 'exit' to stop")
        print("\nExamples:")
        print('  "Take off to 2 meters and form a circle"')
        print('  "Move drone 0 to position 3,2,1.5"')
        print('  "Land all drones"')
        print("="*70 + "\n")

        while True:
            try:
                user_input = input("\n🚁 Command> ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("[Controller] Exiting interactive mode")
                    break

                if user_input.lower() == 'state':
                    state = self.api_client.get_state()
                    if state:
                        print("\n" + self.env_translator.state_to_text(state))
                    else:
                        print("[Controller] Could not fetch state")
                    continue

                # Check for dry-run mode
                execute = True
                if user_input.lower().startswith('dry '):
                    execute = False
                    user_input = user_input[4:].strip()
                    print("[Controller] DRY RUN MODE - No execution")

                # Process command
                result = self.process_command(user_input, execute=execute)

                if not result["success"]:
                    print(f"\n❌ Error: {result.get('error', 'Unknown error')}")
                elif not execute:
                    print("\n✓ Plan generated (not executed)")
                else:
                    print(f"\n✓ Mission completed successfully")
                    print(f"   Success rate: {result['execution_result']['success_rate']:.1f}%")

            except KeyboardInterrupt:
                print("\n[Controller] Interrupted by user")
                break
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")

        print("\n[Controller] Goodbye!\n")


# Example usage functions
def example_basic_commands():
    """Example: Basic command execution."""
    controller = AgenticSwarmController()

    commands = [
        "Take off all drones to 1.5 meters",
        "Form a circle at altitude 2 meters with radius 2 meters",
        "Land all drones"
    ]

    for cmd in commands:
        result = controller.process_command(cmd)
        input("\nPress Enter to continue...")


def example_complex_mission():
    """Example: Complex multi-step mission."""
    controller = AgenticSwarmController()

    command = """
    Execute a surveillance pattern:
    1. Take off to 2 meters
    2. Form a line along the x-axis
    3. Wait 5 seconds
    4. Form a grid pattern
    5. Return to landing positions
    """

    result = controller.process_command(command)
    print("\n" + json.dumps(result["mission_plan"], indent=2))


def example_individual_control():
    """Example: Control individual drones."""
    controller = AgenticSwarmController()

    command = "Send drone 0 to position (3, 2, 1.5) and drone 1 to position (-2, 3, 2.0)"

    result = controller.process_command(command)


if __name__ == "__main__":
    # Run interactive mode by default
    controller = AgenticSwarmController()
    controller.interactive_mode()
