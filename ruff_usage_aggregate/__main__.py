import os.path

import envparse


def main():
    if os.path.isfile(".env"):
        envparse.Env.read_envfile(".env")
    from ruff_usage_aggregate.cli import main

    main(auto_envvar_prefix="RUA")


if __name__ == "__main__":
    main()
