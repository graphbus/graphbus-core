"""
Tests for Docker command
"""

import pytest
from pathlib import Path
from click.testing import CliRunner

from graphbus_cli.commands.docker import docker, _generate_dockerfile, _generate_docker_compose


class TestDockerGenerate:
    """Test docker generate command"""

    @pytest.fixture
    def runner(self):
        """Create CLI runner"""
        return CliRunner()

    def test_generate_basic_dockerfile(self, runner, tmp_path):
        """Test generating basic Dockerfile"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(docker, ['generate'])
            assert result.exit_code == 0
            assert 'Generated Dockerfile' in result.output

            # Check file exists
            dockerfile = Path('Dockerfile')
            assert dockerfile.exists()

            # Check content
            content = dockerfile.read_text()
            assert 'FROM python:3.11-slim' in content
            assert 'WORKDIR /app' in content
            assert 'COPY requirements.txt' in content
            assert 'CMD ["graphbus", "run", ".graphbus"]' in content

    def test_generate_multi_stage_dockerfile(self, runner, tmp_path):
        """Test generating multi-stage Dockerfile"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(docker, ['generate', '--multi-stage'])
            assert result.exit_code == 0

            content = Path('Dockerfile').read_text()
            assert 'AS builder' in content
            assert 'Build stage' in content
            assert 'Runtime stage' in content
            assert 'COPY --from=builder' in content

    def test_generate_with_health_check(self, runner, tmp_path):
        """Test generating Dockerfile with health check"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(docker, ['generate', '--health-check'])
            assert result.exit_code == 0

            content = Path('Dockerfile').read_text()
            assert 'HEALTHCHECK' in content
            assert 'http://localhost:8080/health' in content

    def test_generate_with_state_volume(self, runner, tmp_path):
        """Test generating Dockerfile with state volume"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(docker, ['generate', '--state-volume'])
            assert result.exit_code == 0

            content = Path('Dockerfile').read_text()
            assert 'VOLUME ["/app/state"]' in content

    def test_generate_custom_python_version(self, runner, tmp_path):
        """Test generating Dockerfile with custom Python version"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(docker, ['generate', '--python-version', '3.10'])
            assert result.exit_code == 0

            content = Path('Dockerfile').read_text()
            assert 'FROM python:3.10-slim' in content

    def test_generate_custom_output(self, runner, tmp_path):
        """Test generating Dockerfile to custom path"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(docker, ['generate', '--output', 'custom.dockerfile'])
            assert result.exit_code == 0

            custom_file = Path('custom.dockerfile')
            assert custom_file.exists()
            assert 'FROM python:3.11-slim' in custom_file.read_text()

    def test_generate_overwrite_confirmation(self, runner, tmp_path):
        """Test overwrite confirmation when file exists"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create initial file
            Path('Dockerfile').write_text('existing content')

            # Try to generate again with 'no' response
            result = runner.invoke(docker, ['generate'], input='n\n')
            assert result.exit_code == 0
            assert 'already exists' in result.output
            assert 'Cancelled' in result.output

            # File should remain unchanged
            assert Path('Dockerfile').read_text() == 'existing content'

    def test_generate_overwrite_yes(self, runner, tmp_path):
        """Test overwriting existing Dockerfile"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create initial file
            Path('Dockerfile').write_text('existing content')

            # Generate again with 'yes' response
            result = runner.invoke(docker, ['generate'], input='y\n')
            assert result.exit_code == 0
            assert 'Generated Dockerfile' in result.output

            # File should be updated
            assert 'FROM python:3.11-slim' in Path('Dockerfile').read_text()


class TestDockerCompose:
    """Test docker compose command"""

    @pytest.fixture
    def runner(self):
        """Create CLI runner"""
        return CliRunner()

    def test_compose_basic(self, runner, tmp_path):
        """Test generating basic docker-compose.yml"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(docker, ['compose'])
            assert result.exit_code == 0
            assert 'Generated docker-compose.yml' in result.output

            compose_file = Path('docker-compose.yml')
            assert compose_file.exists()

            content = compose_file.read_text()
            assert 'version: ' in content
            assert 'services:' in content
            assert 'graphbus:' in content
            assert 'image: graphbus-app:latest' in content

    def test_compose_with_redis(self, runner, tmp_path):
        """Test generating docker-compose.yml with Redis"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(docker, ['compose', '--with-redis'])
            assert result.exit_code == 0

            content = Path('docker-compose.yml').read_text()
            assert 'redis:' in content
            assert 'image: redis:7-alpine' in content
            assert 'depends_on:' in content
            assert 'redis-data:' in content

    def test_compose_with_postgres(self, runner, tmp_path):
        """Test generating docker-compose.yml with PostgreSQL"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(docker, ['compose', '--with-postgres'])
            assert result.exit_code == 0

            content = Path('docker-compose.yml').read_text()
            assert 'postgres:' in content
            assert 'image: postgres:15-alpine' in content
            assert 'POSTGRES_DB=graphbus' in content
            assert 'postgres-data:' in content

    def test_compose_with_both(self, runner, tmp_path):
        """Test generating docker-compose.yml with Redis and PostgreSQL"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(docker, ['compose', '--with-redis', '--with-postgres'])
            assert result.exit_code == 0

            content = Path('docker-compose.yml').read_text()
            assert 'redis:' in content
            assert 'postgres:' in content
            assert 'redis-data:' in content
            assert 'postgres-data:' in content
            assert content.count('depends_on:') >= 1

    def test_compose_custom_output(self, runner, tmp_path):
        """Test generating docker-compose.yml to custom path"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(docker, ['compose', '--output', 'custom-compose.yml'])
            assert result.exit_code == 0

            custom_file = Path('custom-compose.yml')
            assert custom_file.exists()


class TestDockerfileGeneration:
    """Test Dockerfile generation functions"""

    def test_generate_basic_dockerfile_content(self):
        """Test basic Dockerfile content generation"""
        dockerfile = _generate_dockerfile(
            python_version='3.11',
            multi_stage=False,
            health_check=False,
            state_volume=False
        )

        assert 'FROM python:3.11-slim' in dockerfile
        assert 'WORKDIR /app' in dockerfile
        assert 'COPY requirements.txt' in dockerfile
        assert 'RUN pip install' in dockerfile
        assert 'COPY agents/' in dockerfile
        assert 'COPY .graphbus/' in dockerfile
        assert 'CMD ["graphbus", "run", ".graphbus"]' in dockerfile

    def test_generate_multistage_dockerfile_content(self):
        """Test multi-stage Dockerfile content"""
        dockerfile = _generate_dockerfile(
            python_version='3.11',
            multi_stage=True,
            health_check=False,
            state_volume=False
        )

        assert 'AS builder' in dockerfile
        assert 'Build stage' in dockerfile
        assert 'Runtime stage' in dockerfile
        assert 'COPY --from=builder' in dockerfile
        assert 'ENV PATH=/root/.local/bin:$PATH' in dockerfile

    def test_generate_dockerfile_with_healthcheck(self):
        """Test Dockerfile with health check"""
        dockerfile = _generate_dockerfile(
            python_version='3.11',
            multi_stage=False,
            health_check=True,
            state_volume=False
        )

        assert 'HEALTHCHECK' in dockerfile
        assert '--interval=30s' in dockerfile
        assert 'http://localhost:8080/health' in dockerfile

    def test_generate_dockerfile_with_volume(self):
        """Test Dockerfile with volume"""
        dockerfile = _generate_dockerfile(
            python_version='3.11',
            multi_stage=False,
            health_check=False,
            state_volume=True
        )

        assert 'VOLUME ["/app/state"]' in dockerfile

    def test_generate_dockerfile_all_options(self):
        """Test Dockerfile with all options enabled"""
        dockerfile = _generate_dockerfile(
            python_version='3.10',
            multi_stage=True,
            health_check=True,
            state_volume=True
        )

        assert 'FROM python:3.10-slim' in dockerfile
        assert 'AS builder' in dockerfile
        assert 'HEALTHCHECK' in dockerfile
        assert 'VOLUME ["/app/state"]' in dockerfile


class TestDockerComposeGeneration:
    """Test docker-compose.yml generation function"""

    def test_generate_basic_compose(self):
        """Test basic docker-compose.yml generation"""
        compose = _generate_docker_compose(with_redis=False, with_postgres=False)

        assert 'version:' in compose
        assert 'services:' in compose
        assert 'graphbus:' in compose
        assert 'image: graphbus-app:latest' in compose
        assert '8080:8080' in compose
        assert 'redis:' not in compose
        assert 'postgres:' not in compose

    def test_generate_compose_with_redis(self):
        """Test docker-compose.yml with Redis"""
        compose = _generate_docker_compose(with_redis=True, with_postgres=False)

        assert 'redis:' in compose
        assert 'image: redis:7-alpine' in compose
        assert 'depends_on:' in compose
        assert '6379:6379' in compose
        assert 'redis-data:' in compose

    def test_generate_compose_with_postgres(self):
        """Test docker-compose.yml with PostgreSQL"""
        compose = _generate_docker_compose(with_redis=False, with_postgres=True)

        assert 'postgres:' in compose
        assert 'image: postgres:15-alpine' in compose
        assert 'POSTGRES_DB=graphbus' in compose
        assert '5432:5432' in compose
        assert 'postgres-data:' in compose

    def test_generate_compose_with_both_services(self):
        """Test docker-compose.yml with both Redis and PostgreSQL"""
        compose = _generate_docker_compose(with_redis=True, with_postgres=True)

        assert 'redis:' in compose
        assert 'postgres:' in compose
        assert 'depends_on:' in compose
        assert 'redis-data:' in compose
        assert 'postgres-data:' in compose
        assert 'volumes:' in compose
