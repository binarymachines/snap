version: 1
disable_existing_loggers: False
formatters:
    simple:
        format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

handlers:
    console:
        class: logging.StreamHandler
        level: DEBUG
        formatter: simple
        stream: ext://sys.stdout

    file_handler:
        class: logging.handlers.RotatingFileHandler
        level: INFO
        formatter: simple
        filename: {{log_filename}}
        maxBytes: 10485760 # 10MB
        backupCount: 20
        encoding: utf8

loggers:
    root:
        level: INFO
        handlers: [console]
        propagate: no

    sqlalchemy:
        level: ERROR
        handlers: [console]
        propagate: no

    request:
        level: INFO
        handlers: [console]
        propagate: no

    init:
        level: INFO
        handlers: [console]
        propagate: no

    service:
        level: INFO
        handlers: [console]
        propagate: no

    transform:
        level: INFO
        handlers: [console]
        propagate: no

root:
    level: INFO
    handlers: [console, file_handler]