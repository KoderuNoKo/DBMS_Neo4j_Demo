from config import Config
from exporter import DataExporter

# Default: 50 patients per batch
config = Config()
exporter = DataExporter(config, batch_size=50)
exporter.export()

# Custom batch size
exporter = DataExporter(config, batch_size=100)
exporter.export()