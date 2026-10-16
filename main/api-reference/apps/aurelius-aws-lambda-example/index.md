# aurelius-aws-lambda-example

This is an example AWS Lambda application.

## Deployment

Deploy using the provided Dockerfile.

## Configuration

Configuration is managed via the `Settings` model:

> [!NOTE]
>
> **Settings**
>
> ## aurelius\_aws\_lambda\_example.models.Settings
>
> Bases: `BaseSettings`
>
> Settings for the application.
>
> **Show JSON schema:**
>
> ```
> {
>   "$defs": {
>     "Environment": {
>       "enum": [
>         "development",
>         "production"
>       ],
>       "type": "string"
>     }
>   },
>   "additionalProperties": false,
>   "description": "Settings for the application.",
>   "properties": {
>     "aws_region": {
>       "description": "AWS region for the application.",
>       "title": "Aws Region",
>       "type": "string"
>     },
>     "environment": {
>       "$ref": "#/$defs/Environment",
>       "default": "production",
>       "description": "The environment the application is running in."
>     },
>     "kafka_bootstrap_servers": {
>       "description": "Comma-separated list of Kafka brokers to connect to.",
>       "title": "Kafka Bootstrap Servers",
>       "type": "string"
>     },
>     "kafka_topic_name": {
>       "description": "Name of the Kafka topic to produce messages to.",
>       "title": "Kafka Topic Name",
>       "type": "string"
>     },
>     "log_level": {
>       "default": "INFO",
>       "description": "Minimum log level to display at runtime.",
>       "title": "Log Level",
>       "type": "string"
>     },
>     "schema_registry_url": {
>       "description": "URL of the schema registry.",
>       "format": "uri",
>       "maxLength": 2083,
>       "minLength": 1,
>       "title": "Schema Registry Url",
>       "type": "string"
>     }
>   },
>   "required": [
>     "aws_region",
>     "kafka_bootstrap_servers",
>     "kafka_topic_name",
>     "schema_registry_url"
>   ],
>   "title": "Settings",
>   "type": "object"
> }
> ```
>
> Fields:
>
> - `aws_region` (`str`)
> - `environment` (`Environment`)
> - `kafka_bootstrap_servers` (`str`)
> - `kafka_topic_name` (`str`)
> - `log_level` (`str`)
> - `schema_registry_url` (`HttpUrl`)
>
> ### aws\_region
>
> ```
> aws_region: str
> ```
>
> AWS region for the application.
>
> ### environment
>
> ```
> environment: Environment = 'production'
> ```
>
> The environment the application is running in.
>
> ### is\_development
>
> ```
> is_development: bool
> ```
>
> Check if the application is running in a development environment.
>
> ### kafka\_bootstrap\_servers
>
> ```
> kafka_bootstrap_servers: str
> ```
>
> Comma-separated list of Kafka brokers to connect to.
>
> ### kafka\_topic\_name
>
> ```
> kafka_topic_name: str
> ```
>
> Name of the Kafka topic to produce messages to.
>
> ### log\_level
>
> ```
> log_level: str = 'INFO'
> ```
>
> Minimum log level to display at runtime.
>
> ### schema\_registry\_url
>
> ```
> schema_registry_url: HttpUrl
> ```
>
> URL of the schema registry.

You can set configuration options using environment variables.
