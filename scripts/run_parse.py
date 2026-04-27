import argparse
import asyncio

from marketplace_parse.parsers.runner import run_parse


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a parse job against a product_urls row.")
    parser.add_argument("--url-id", type=int, required=True)
    args = parser.parse_args()

    n = asyncio.run(run_parse(args.url_id))
    print(f"Collected {n} reviews (url_id={args.url_id})")


if __name__ == "__main__":
    main()
