from config import Config
from exporter import DataExporter

def main():
    """Main entry point."""
    config = Config()
    exporter = DataExporter(config)
    exporter.export()


if __name__ == "__main__":
    main()