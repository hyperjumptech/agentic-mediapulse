import argparse
import asyncio

from dotenv import load_dotenv

load_dotenv()

from agents.campaign import run_campaign
from utils.db import fetch_subscriptions


def main() -> None:
    parser = argparse.ArgumentParser(prog="cli", description="Local testing CLI; mirrors the API.")
    commands = parser.add_subparsers(dest="command", required=True)

    run_command = commands.add_parser("run", help="Run the full campaign for all subscribers (like POST /run).")
    run_command.add_argument("--send", action="store_true", help="Actually email subscribers (default: dry-run).")

    test_command = commands.add_parser("test", help="Run one user's followed tickers (like POST /test).")
    test_command.add_argument("--email", required=True, help="Subscriber email to run for.")
    test_command.add_argument("--send", action="store_true", help="Actually email the user (default: dry-run).")

    args = parser.parse_args()

    if args.command == "run":
        asyncio.run(run_campaign(send=args.send))
    elif args.command == "test":
        subscriptions = fetch_subscriptions(email=args.email)
        asyncio.run(run_campaign(subscriptions=subscriptions, send=args.send))


if __name__ == "__main__":
    main()
