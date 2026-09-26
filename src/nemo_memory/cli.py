"""Command line interface for local, source-cited retrieval."""

import argparse
import json
import sys

from .retrieval import RetrievalError, evaluate_fixture, index_directory, search_index


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nemo")
    commands = parser.add_subparsers(dest="command", required=True)

    index = commands.add_parser("index", help="Index an explicitly chosen directory")
    index.add_argument("root", metavar="ROOT")
    index.add_argument("--db", required=True, metavar="INDEX")
    index.add_argument("--json", action="store_true")

    search = commands.add_parser("search", help="Search an existing index")
    search.add_argument("query", metavar="QUERY")
    search.add_argument("--db", required=True, metavar="INDEX")
    search.add_argument("--json", action="store_true")

    evaluate = commands.add_parser("evaluate", help="Evaluate a fixture directory")
    evaluate.add_argument("fixture_dir", metavar="FIXTURE_DIR")
    evaluate.add_argument("--json", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "index":
            result = index_directory(args.root, args.db)
            if args.json:
                print(json.dumps(result, ensure_ascii=False))
            else:
                print(f"Indexed {result['files']} files and {result['passages']} passages.")
        elif args.command == "search":
            hits = search_index(args.query, args.db)
            if args.json:
                print(json.dumps(hits, ensure_ascii=False))
            else:
                if not hits:
                    print("No matching passages.")
                for hit in hits:
                    print(f"{hit['path']}:{hit['start_line']}-{hit['end_line']} "
                          f"({hit['revision']}, score {hit['score']:.6g})")
                    print(hit["text"])
        else:
            evaluation = evaluate_fixture(args.fixture_dir)
            if args.json:
                print(json.dumps(evaluation, ensure_ascii=False))
            else:
                print(f"Queries: {evaluation['query_count']}")
                print(f"Recall@10: {evaluation['recall_at_10']:.3f}")
                print(f"nDCG@10: {evaluation['ndcg_at_10']:.3f}")
                print(f"Unanswerable: {evaluation['unanswerable_count']} "
                      f"({evaluation['unanswerable_false_hits']} with hits)")
    except RetrievalError as exc:
        print(f"nemo: {exc}", file=sys.stderr)
        return 1
    return 0
