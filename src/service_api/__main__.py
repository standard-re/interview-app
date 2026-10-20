import uvicorn

from service_api.config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "service_api.app:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "local",
    )


if __name__ == "__main__":
    main()
