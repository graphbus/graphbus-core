"""
Docker command - Generate Dockerfiles and manage containers
"""

import click
import subprocess
from pathlib import Path
from typing import Optional

from graphbus_cli.utils.output import (
    console, print_success, print_error, print_info,
    print_header, print_warning
)
from graphbus_cli.utils.errors import CLIError


@click.group()
def docker():
    """
    Docker containerization tools.

    \b
    Generate Dockerfiles and manage GraphBus containers.

    \b
    Examples:
      graphbus docker generate              # Generate Dockerfile
      graphbus docker generate --multi-stage  # Multi-stage build
      graphbus docker build                 # Build Docker image
      graphbus docker run                   # Run container
      graphbus docker compose               # Generate docker-compose.yml
    """
    pass


@docker.command()
@click.option(
    '--output',
    type=click.Path(dir_okay=False),
    default='Dockerfile',
    help='Output Dockerfile path (default: Dockerfile)'
)
@click.option(
    '--multi-stage',
    is_flag=True,
    help='Generate multi-stage build for smaller images'
)
@click.option(
    '--python-version',
    default='3.11',
    help='Python version (default: 3.11)'
)
@click.option(
    '--health-check',
    is_flag=True,
    help='Include health check endpoint'
)
@click.option(
    '--state-volume',
    is_flag=True,
    help='Add volume mount for state persistence'
)
def generate(output: str, multi_stage: bool, python_version: str, health_check: bool, state_volume: bool):
    """
    Generate Dockerfile for GraphBus application.

    \b
    Creates a production-ready Dockerfile with:
      - Python base image
      - Dependency installation
      - GraphBus CLI setup
      - Optional health checks
      - Optional state persistence
    """
    try:
        print_header("Generating Dockerfile")

        output_path = Path(output)

        # Check if file exists
        if output_path.exists():
            print_warning(f"{output} already exists")
            if not click.confirm("Overwrite?"):
                print_info("Cancelled")
                return

        # Generate Dockerfile content
        dockerfile = _generate_dockerfile(
            python_version=python_version,
            multi_stage=multi_stage,
            health_check=health_check,
            state_volume=state_volume
        )

        # Write to file
        output_path.write_text(dockerfile)

        print_success(f"Generated {output}")
        console.print()

        # Show next steps
        print_info("Next steps:")
        console.print("  1. Review the Dockerfile")
        console.print("  2. Build: docker build -t graphbus-app .")
        console.print("  3. Run: docker run -p 8080:8080 graphbus-app")

    except Exception as e:
        raise CLIError(f"Failed to generate Dockerfile: {str(e)}")


@docker.command()
@click.option(
    '--tag',
    '-t',
    default='graphbus-app:latest',
    help='Docker image tag (default: graphbus-app:latest)'
)
@click.option(
    '--dockerfile',
    '-f',
    type=click.Path(exists=True),
    default='Dockerfile',
    help='Path to Dockerfile (default: Dockerfile)'
)
@click.option(
    '--no-cache',
    is_flag=True,
    help='Build without using cache'
)
def build(tag: str, dockerfile: str, no_cache: bool):
    """
    Build Docker image for GraphBus application.

    \b
    Builds a Docker image using the generated Dockerfile.
    """
    try:
        print_header(f"Building Docker Image: {tag}")

        # Check if Dockerfile exists
        if not Path(dockerfile).exists():
            print_error(f"{dockerfile} not found")
            print_info("Generate one with: graphbus docker generate")
            raise click.Abort()

        # Build docker image
        cmd = ['docker', 'build', '-t', tag, '-f', dockerfile]
        if no_cache:
            cmd.append('--no-cache')
        cmd.append('.')

        console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")
        console.print()

        result = subprocess.run(cmd, capture_output=False)

        if result.returncode == 0:
            console.print()
            print_success(f"Image built successfully: {tag}")
        else:
            raise CLIError(f"Docker build failed with exit code {result.returncode}")

    except FileNotFoundError:
        raise CLIError("Docker not found. Please install Docker first.")
    except Exception as e:
        raise CLIError(f"Failed to build Docker image: {str(e)}")


@docker.command()
@click.option(
    '--tag',
    '-t',
    default='graphbus-app:latest',
    help='Docker image tag (default: graphbus-app:latest)'
)
@click.option(
    '--port',
    '-p',
    default='8080:8080',
    help='Port mapping (default: 8080:8080)'
)
@click.option(
    '--name',
    default='graphbus-runtime',
    help='Container name (default: graphbus-runtime)'
)
@click.option(
    '--detach',
    '-d',
    is_flag=True,
    help='Run container in background'
)
@click.option(
    '--volume',
    '-v',
    multiple=True,
    help='Volume mounts (e.g., ./state:/app/state)'
)
def run(tag: str, port: str, name: str, detach: bool, volume: tuple):
    """
    Run GraphBus application in Docker container.

    \b
    Starts a Docker container from the built image.
    """
    try:
        print_header(f"Running Container: {name}")

        # Build docker run command
        cmd = ['docker', 'run', '--name', name, '-p', port]

        if detach:
            cmd.append('-d')

        for vol in volume:
            cmd.extend(['-v', vol])

        cmd.append(tag)

        console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")
        console.print()

        result = subprocess.run(cmd, capture_output=False)

        if result.returncode == 0:
            console.print()
            if detach:
                print_success(f"Container {name} started in background")
                print_info(f"View logs: docker logs {name}")
                print_info(f"Stop: docker stop {name}")
            else:
                print_success(f"Container {name} stopped")
        else:
            raise CLIError(f"Docker run failed with exit code {result.returncode}")

    except FileNotFoundError:
        raise CLIError("Docker not found. Please install Docker first.")
    except Exception as e:
        raise CLIError(f"Failed to run Docker container: {str(e)}")


@docker.command()
@click.option(
    '--output',
    type=click.Path(dir_okay=False),
    default='docker-compose.yml',
    help='Output file path (default: docker-compose.yml)'
)
@click.option(
    '--with-redis',
    is_flag=True,
    help='Include Redis service'
)
@click.option(
    '--with-postgres',
    is_flag=True,
    help='Include PostgreSQL service'
)
def compose(output: str, with_redis: bool, with_postgres: bool):
    """
    Generate docker-compose.yml for multi-container setup.

    \b
    Creates a docker-compose.yml with:
      - GraphBus runtime service
      - Optional Redis for message persistence
      - Optional PostgreSQL for state storage
    """
    try:
        print_header("Generating docker-compose.yml")

        output_path = Path(output)

        # Check if file exists
        if output_path.exists():
            print_warning(f"{output} already exists")
            if not click.confirm("Overwrite?"):
                print_info("Cancelled")
                return

        # Generate docker-compose content
        compose_content = _generate_docker_compose(
            with_redis=with_redis,
            with_postgres=with_postgres
        )

        # Write to file
        output_path.write_text(compose_content)

        print_success(f"Generated {output}")
        console.print()

        # Show next steps
        print_info("Next steps:")
        console.print("  1. Review docker-compose.yml")
        console.print("  2. Start services: docker-compose up -d")
        console.print("  3. View logs: docker-compose logs -f")
        console.print("  4. Stop services: docker-compose down")

    except Exception as e:
        raise CLIError(f"Failed to generate docker-compose.yml: {str(e)}")


def _generate_dockerfile(
    python_version: str,
    multi_stage: bool,
    health_check: bool,
    state_volume: bool
) -> str:
    """Generate Dockerfile content"""

    if multi_stage:
        # Multi-stage build for smaller images
        dockerfile = f"""# Multi-stage build for GraphBus application
# Build stage
FROM python:{python_version}-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:{python_version}-slim

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY agents/ agents/
COPY .graphbus/ .graphbus/

"""
    else:
        # Standard single-stage build
        dockerfile = f"""# GraphBus application Dockerfile
FROM python:{python_version}-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY agents/ agents/
COPY .graphbus/ .graphbus/

"""

    # Add volume for state persistence
    if state_volume:
        dockerfile += """# Volume for state persistence
VOLUME ["/app/state"]

"""

    # Add health check
    if health_check:
        dockerfile += """# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD python -c "import requests; requests.get('http://localhost:8080/health').raise_for_status()" || exit 1

"""

    # Add labels
    dockerfile += """# Labels
LABEL org.opencontainers.image.title="GraphBus Application"
LABEL org.opencontainers.image.description="Multi-agent orchestration runtime"
LABEL org.opencontainers.image.vendor="GraphBus"

"""

    # Add default command
    dockerfile += """# Expose port (if using dashboard)
EXPOSE 8080

# Default command
CMD ["graphbus", "run", ".graphbus"]
"""

    return dockerfile


def _generate_docker_compose(with_redis: bool, with_postgres: bool) -> str:
    """Generate docker-compose.yml content"""

    compose = """version: '3.8'

services:
  graphbus:
    build: .
    image: graphbus-app:latest
    container_name: graphbus-runtime
    ports:
      - "8080:8080"
    environment:
      - GRAPHBUS_ENV=production
    volumes:
      - ./state:/app/state
    restart: unless-stopped
"""

    if with_redis:
        compose += """    depends_on:
      - redis
"""

    if with_postgres:
        if not with_redis:
            compose += """    depends_on:
      - postgres
"""
        else:
            compose += """      - postgres
"""

    if with_redis:
        compose += """
  redis:
    image: redis:7-alpine
    container_name: graphbus-redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    restart: unless-stopped
"""

    if with_postgres:
        compose += """
  postgres:
    image: postgres:15-alpine
    container_name: graphbus-postgres
    environment:
      - POSTGRES_DB=graphbus
      - POSTGRES_USER=graphbus
      - POSTGRES_PASSWORD=graphbus
    ports:
      - "5432:5432"
    volumes:
      - postgres-data:/var/lib/postgresql/data
    restart: unless-stopped
"""

    # Add volumes section if needed
    if with_redis or with_postgres:
        compose += """
volumes:
"""
        if with_redis:
            compose += """  redis-data:
"""
        if with_postgres:
            compose += """  postgres-data:
"""

    return compose
