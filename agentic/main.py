#!/usr/bin/env python3
"""
AUS-Lab Agentic Controller - Main CLI
Simple command-line interface for LLM-driven swarm control.
"""

import argparse
import sys
from agentic_controller import AgenticSwarmController


def main():
    parser = argparse.ArgumentParser(
        description="LLM-Powered UAV Swarm Controller",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python main.py

  # Single command execution
  python main.py -c "Take off to 2 meters and form a circle"

  # Dry run (plan only, no execution)
  python main.py -c "Survey the area" --dry-run

  # Specify custom API endpoint
  python main.py --api http://192.168.1.100:8000 -c "Land all drones"

  # Use different Gemini model
  python main.py --model gemini-pro -c "Form a line"
        """
    )

    parser.add_argument(
        "-c", "--command",
        type=str,
        help="Natural language command to execute"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate plan without executing (dry run)"
    )

    parser.add_argument(
        "--api",
        type=str,
        default="http://localhost:8000",
        help="Simulation API base URL (default: http://localhost:8000)"
    )

    parser.add_argument(
        "--model",
        type=str,
        default="models/gemini-flash-latest",
        help="Gemini model to use (default: models/gemini-flash-latest)"
    )

    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Start interactive mode (default if no command given)"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    # Initialize controller
    try:
        controller = AgenticSwarmController(
            api_base_url=args.api,
            gemini_model=args.model
        )
    except Exception as e:
        print(f"❌ Failed to initialize controller: {e}")
        print("\nTroubleshooting:")
        print("  1. Make sure .env file exists with GEMINI_API_KEY")
        print("  2. Ensure simulation is running: cd ../simulation && python main.py")
        return 1

    # Execute based on mode
    if args.command:
        # Single command mode
        print(f"\n{'='*70}")
        print(f"  Executing Command")
        print(f"{'='*70}")
        print(f"\nCommand: \"{args.command}\"")
        print(f"Mode: {'DRY RUN' if args.dry_run else 'EXECUTE'}")
        print(f"API: {args.api}")
        print(f"Model: {args.model}\n")

        try:
            result = controller.process_command(args.command, execute=not args.dry_run)

            if result["success"]:
                print(f"\n{'='*70}")
                print("  ✓ SUCCESS")
                print(f"{'='*70}")

                if args.dry_run:
                    print("\nGenerated Mission Plan:")
                    print(f"  Name: {result['mission_plan']['mission_name']}")
                    print(f"  Actions: {len(result['mission_plan']['actions'])}")
                    for idx, action in enumerate(result['mission_plan']['actions'], 1):
                        print(f"    {idx}. {action['action_type']} - {action['parameters']}")
                else:
                    exec_result = result['execution_result']
                    print(f"\nMission: {exec_result['mission_name']}")
                    print(f"Success Rate: {exec_result['success_rate']:.1f}%")
                    print(f"Total Time: {exec_result['total_time']:.2f}s")
                    print(f"Actions: {exec_result['successful_actions']}/{exec_result['total_actions']}")

                    if args.verbose and result.get('final_summary'):
                        print("\nFinal State:")
                        print(result['final_summary'])

                return 0
            else:
                print(f"\n{'='*70}")
                print("  ✗ FAILED")
                print(f"{'='*70}")
                print(f"\nError: {result.get('error', 'Unknown error')}")
                return 1

        except KeyboardInterrupt:
            print("\n\n⚠ Interrupted by user")
            return 130
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            return 1

    else:
        # Interactive mode (default)
        print("\nNo command specified, starting interactive mode...")
        print("(Use -c flag for single command execution, --help for more options)\n")
        try:
            controller.interactive_mode()
            return 0
        except KeyboardInterrupt:
            print("\n\n⚠ Interrupted by user")
            return 130


if __name__ == "__main__":
    sys.exit(main())
