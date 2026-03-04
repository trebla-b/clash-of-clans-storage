from app.config import load_config


def main() -> int:
    config = load_config()
    print(config.fetch_cron)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
