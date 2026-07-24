import argparse
import webbrowser

MISSING = ("The demo requires the 'demo' extra:\n"
           "pip install pytypehintweb[demo]")


BROWSER_HOSTS = {
    "0.0.0.0": "127.0.0.1",
    "::": "[::1]",
    "::0": "[::1]",
}


def _load():
    try:
        import fastapi  # noqa: F401
        import uvicorn
    except ImportError:
        raise SystemExit(MISSING) from None

    from pytypehintweb.demo import app as demo

    return uvicorn, demo


def _url(host: str, port: int) -> str:
    resolved = BROWSER_HOSTS.get(host, host)

    # An IPv6 literal must be bracketed in a URL authority, or the colons
    # collide with the port separator. Wildcard binds resolve above to an
    # already-bracketed loopback, so bracket only a bare colon-bearing host.
    if ":" in resolved and not resolved.startswith("["):
        resolved = f"[{resolved}]"

    return f"http://{resolved}:{port}"


def main():
    parser = argparse.ArgumentParser(prog="pytypehintweb-demo")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    uvicorn, demo = _load()

    if not args.no_browser:
        url = _url(args.host, args.port)
        demo.ON_STARTUP.append(lambda: webbrowser.open(url))

    uvicorn.run(demo.app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
