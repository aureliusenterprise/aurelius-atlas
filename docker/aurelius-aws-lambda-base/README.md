# aurelius-aws-lambda-base

Hardened Docker base image for Aurelius Python Lambda functions: the AWS Lambda
Runtime Interface Client (RIC), the CloudWatch Lambda Insights extension, and a
non-root Python 3.14 runtime.

Part of the optional **AWS Lambda slice** — remove this project together with
the rest of that slice.

## How it works

- Multi-stage `Dockerfile`: a `dhi.io/python:3.14-debian13-dev` builder installs
  `awslambdaric==4.0.4` into `/var/task` and unpacks the Lambda Insights extension
  into `/opt/cloudwatch`; the runtime stage is `dhi.io/python:3.14-debian13`.
- `USER nonroot`, `PYTHONPATH=/var/task`, and
  `ENTRYPOINT ["python", "-m", "awslambdaric"]` — the handler is supplied as the
  image `CMD` (e.g. `aurelius_aws_lambda_example.main`).
- This image is not semver-versioned: `nx release` skips it (noop version
  actions), so it is tagged `local`/`latest` only. Consumers resolve it via
  `--build-arg VERSION={args.version}`, which falls back to the
  `ARG VERSION=local` default in their Dockerfiles.

## Consuming

Lambda apps pin the image by version tag, which `nx release` keeps in sync:

```dockerfile
FROM ghcr.io/aureliusenterprise/aurelius-aws-lambda-base:${VERSION}
```

Build it with:

```bash
nx docker-build aurelius-aws-lambda-base
```

(`VERSION` defaults to `local` for development builds.)
