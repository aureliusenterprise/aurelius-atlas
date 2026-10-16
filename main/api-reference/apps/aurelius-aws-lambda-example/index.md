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
>     "AWS_REGION": {
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
>     "kafka_ca_file": {
>       "default": "",
>       "description": "PEM CA bundle used to verify the Kafka broker and Schema Registry over TLS. Empty uses the operating system default trust store.",
>       "title": "Kafka Ca File",
>       "type": "string"
>     },
>     "kafka_topic_name": {
>       "description": "Name of the Kafka topic to produce messages to.",
>       "title": "Kafka Topic Name",
>       "type": "string"
>     },
>     "kafka_oauth_token_endpoint_url": {
>       "default": "",
>       "description": "OIDC token endpoint used to fetch OAUTHBEARER tokens for the Kafka broker. Empty means the broker is reached without SASL (e.g. mTLS or plaintext).",
>       "title": "Kafka Oauth Token Endpoint Url",
>       "type": "string"
>     },
>     "kafka_oauth_client_id": {
>       "default": "",
>       "description": "Keycloak client id for the OAuth client-credentials grant.",
>       "title": "Kafka Oauth Client Id",
>       "type": "string"
>     },
>     "kafka_oauth_client_secret": {
>       "default": "",
>       "description": "Keycloak client secret for the OAuth client-credentials grant. A SecretStr so repr/str (and therefore logging) never leak it; callers unwrap with get_secret_value().",
>       "format": "password",
>       "title": "Kafka Oauth Client Secret",
>       "type": "string",
>       "writeOnly": true
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
>     "AWS_REGION",
>     "kafka_bootstrap_servers",
>     "kafka_topic_name",
>     "schema_registry_url"
>   ],
>   "title": "Settings",
>   "type": "object"
> }
> ```
>
> Config:
>
> - `env_prefix`: `AURELIUS_LAMBDA_`
>
> Fields:
>
> - `aws_region` (`str`)
> - `environment` (`Environment`)
> - `kafka_bootstrap_servers` (`str`)
> - `kafka_ca_file` (`str`)
> - `kafka_topic_name` (`str`)
> - `kafka_oauth_token_endpoint_url` (`str`)
> - `kafka_oauth_client_id` (`str`)
> - `kafka_oauth_client_secret` (`SecretStr`)
> - `log_level` (`str`)
> - `schema_registry_url` (`HttpUrl`)
>
> Validators:
>
> - `_require_oauth_credentials`
> - `_require_https_token_endpoint` → `kafka_oauth_token_endpoint_url`
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
> ### kafka\_ca\_file
>
> ```
> kafka_ca_file: str = ''
> ```
>
> PEM CA bundle used to verify the Kafka broker and Schema Registry over TLS. Empty uses the operating system default trust store.
>
> ### kafka\_oauth\_client\_id
>
> ```
> kafka_oauth_client_id: str = ''
> ```
>
> Keycloak client id for the OAuth client-credentials grant.
>
> ### kafka\_oauth\_client\_secret
>
> ```
> kafka_oauth_client_secret: SecretStr = SecretStr('')
> ```
>
> Keycloak client secret for the OAuth client-credentials grant. A SecretStr so repr/str (and therefore logging) never leak it; callers unwrap with get\_secret\_value().
>
> ### kafka\_oauth\_token\_endpoint\_url
>
> ```
> kafka_oauth_token_endpoint_url: str = ''
> ```
>
> OIDC token endpoint used to fetch OAUTHBEARER tokens for the Kafka broker. Empty means the broker is reached without SASL (e.g. mTLS or plaintext).
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
> ### model\_config
>
> ```
> model_config = SettingsConfigDict(env_prefix='AURELIUS_LAMBDA_')
> ```
>
> ### schema\_registry\_url
>
> ```
> schema_registry_url: HttpUrl
> ```
>
> URL of the schema registry.

You can set configuration options using environment variables.
