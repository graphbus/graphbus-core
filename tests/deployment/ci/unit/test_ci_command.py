"""
Tests for CI/CD command
"""

import pytest
from pathlib import Path
from click.testing import CliRunner

from graphbus_cli.commands.ci import ci, _generate_github_actions, _generate_gitlab_ci, _generate_jenkinsfile


class TestCICommand:
    """Test ci command"""

    @pytest.fixture
    def runner(self):
        """Create CLI runner"""
        return CliRunner()

    def test_generate_github_actions(self, runner, tmp_path):
        """Test generating GitHub Actions workflow"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(ci, ['--provider', 'github'])
            assert result.exit_code == 0
            assert 'Generated .github/workflows/graphbus-ci.yml' in result.output

            workflow = Path('.github/workflows/graphbus-ci.yml')
            assert workflow.exists()

            content = workflow.read_text()
            assert 'name: GraphBus CI/CD' in content
            assert 'on:' in content
            assert 'jobs:' in content
            assert 'test:' in content
            assert 'pytest' in content

    def test_generate_gitlab_ci(self, runner, tmp_path):
        """Test generating GitLab CI pipeline"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(ci, ['--provider', 'gitlab'])
            assert result.exit_code == 0
            assert 'Generated .gitlab-ci.yml' in result.output

            pipeline = Path('.gitlab-ci.yml')
            assert pipeline.exists()

            content = pipeline.read_text()
            assert 'image: python:3.11-slim' in content
            assert 'stages:' in content
            assert 'test:' in content

    def test_generate_jenkins(self, runner, tmp_path):
        """Test generating Jenkinsfile"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(ci, ['--provider', 'jenkins'])
            assert result.exit_code == 0
            assert 'Generated Jenkinsfile' in result.output

            jenkinsfile = Path('Jenkinsfile')
            assert jenkinsfile.exists()

            content = jenkinsfile.read_text()
            assert 'pipeline {' in content
            assert 'agent any' in content
            assert 'stages {' in content

    def test_generate_with_docker(self, runner, tmp_path):
        """Test generating CI with Docker support"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(ci, ['--provider', 'github', '--with-docker'])
            assert result.exit_code == 0

            content = Path('.github/workflows/graphbus-ci.yml').read_text()
            assert 'docker:' in content
            assert 'docker/build-push-action' in content

    def test_generate_with_k8s(self, runner, tmp_path):
        """Test generating CI with K8s deployment"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(ci, ['--provider', 'github', '--with-k8s'])
            assert result.exit_code == 0

            content = Path('.github/workflows/graphbus-ci.yml').read_text()
            assert 'deploy:' in content
            assert 'kubectl' in content

    def test_generate_all_options(self, runner, tmp_path):
        """Test generating CI with all options"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(ci, ['--provider', 'github', '--with-docker', '--with-k8s'])
            assert result.exit_code == 0

            content = Path('.github/workflows/graphbus-ci.yml').read_text()
            assert 'test:' in content
            assert 'docker:' in content
            assert 'deploy:' in content

    def test_generate_custom_output(self, runner, tmp_path):
        """Test generating CI to custom path"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(ci, ['--provider', 'github', '--output', 'custom-ci.yml'])
            assert result.exit_code == 0

            assert Path('custom-ci.yml').exists()

    def test_overwrite_confirmation(self, runner, tmp_path):
        """Test overwrite confirmation"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create initial file
            Path('.github/workflows').mkdir(parents=True)
            Path('.github/workflows/graphbus-ci.yml').write_text('existing')

            # Try to generate with 'no'
            result = runner.invoke(ci, ['--provider', 'github'], input='n\n')
            assert result.exit_code == 0
            assert 'already exists' in result.output
            assert 'Cancelled' in result.output


class TestGitHubActionsGeneration:
    """Test GitHub Actions generation"""

    def test_basic_github_actions(self):
        """Test basic GitHub Actions workflow"""
        workflow = _generate_github_actions(with_docker=False, with_k8s=False)

        assert 'name: GraphBus CI/CD' in workflow
        assert 'on:' in workflow
        assert 'push:' in workflow
        assert 'pull_request:' in workflow
        assert 'test:' in workflow
        assert 'uses: actions/setup-python@v4' in workflow
        assert 'graphbus validate' in workflow
        assert 'pytest' in workflow
        assert 'graphbus build' in workflow

    def test_github_actions_with_docker(self):
        """Test GitHub Actions with Docker"""
        workflow = _generate_github_actions(with_docker=True, with_k8s=False)

        assert 'docker:' in workflow
        assert 'needs: test' in workflow
        assert 'docker/build-push-action' in workflow
        assert 'DOCKER_USERNAME' in workflow

    def test_github_actions_with_k8s(self):
        """Test GitHub Actions with K8s"""
        workflow = _generate_github_actions(with_docker=True, with_k8s=True)

        assert 'deploy:' in workflow
        assert 'needs: docker' in workflow
        assert 'kubectl apply' in workflow
        assert 'kubectl rollout status' in workflow

    def test_github_actions_all_features(self):
        """Test GitHub Actions with all features"""
        workflow = _generate_github_actions(with_docker=True, with_k8s=True)

        assert 'test:' in workflow
        assert 'docker:' in workflow
        assert 'deploy:' in workflow
        assert workflow.count('jobs:') >= 1
        assert 'coverage' in workflow.lower()


class TestGitLabCIGeneration:
    """Test GitLab CI generation"""

    def test_basic_gitlab_ci(self):
        """Test basic GitLab CI pipeline"""
        pipeline = _generate_gitlab_ci(with_docker=False, with_k8s=False)

        assert 'image: python:3.11-slim' in pipeline
        assert 'stages:' in pipeline
        assert '- test' in pipeline
        assert 'test:' in pipeline
        assert 'graphbus validate' in pipeline
        assert 'pytest' in pipeline
        assert 'coverage:' in pipeline

    def test_gitlab_ci_with_docker(self):
        """Test GitLab CI with Docker"""
        pipeline = _generate_gitlab_ci(with_docker=True, with_k8s=False)

        assert '- docker' in pipeline
        assert 'docker:' in pipeline
        assert 'stage: docker' in pipeline
        assert 'docker build' in pipeline

    def test_gitlab_ci_with_k8s(self):
        """Test GitLab CI with K8s"""
        pipeline = _generate_gitlab_ci(with_docker=True, with_k8s=True)

        assert '- deploy' in pipeline
        assert 'deploy:' in pipeline
        assert 'stage: deploy' in pipeline
        assert 'kubectl apply' in pipeline

    def test_gitlab_ci_all_features(self):
        """Test GitLab CI with all features"""
        pipeline = _generate_gitlab_ci(with_docker=True, with_k8s=True)

        assert 'test:' in pipeline
        assert 'docker:' in pipeline
        assert 'deploy:' in pipeline
        assert 'cache:' in pipeline


class TestJenkinsfileGeneration:
    """Test Jenkinsfile generation"""

    def test_basic_jenkinsfile(self):
        """Test basic Jenkinsfile"""
        jenkinsfile = _generate_jenkinsfile(with_docker=False, with_k8s=False)

        assert 'pipeline {' in jenkinsfile
        assert 'agent any' in jenkinsfile
        assert 'stages {' in jenkinsfile
        assert 'stage(\'Setup\')' in jenkinsfile
        assert 'stage(\'Validate\')' in jenkinsfile
        assert 'stage(\'Test\')' in jenkinsfile
        assert 'stage(\'Build\')' in jenkinsfile
        assert 'pytest' in jenkinsfile

    def test_jenkinsfile_with_docker(self):
        """Test Jenkinsfile with Docker"""
        jenkinsfile = _generate_jenkinsfile(with_docker=True, with_k8s=False)

        assert 'stage(\'Docker Build\')' in jenkinsfile
        assert 'docker.build' in jenkinsfile
        assert 'when {' in jenkinsfile
        assert 'branch \'main\'' in jenkinsfile

    def test_jenkinsfile_with_k8s(self):
        """Test Jenkinsfile with K8s"""
        jenkinsfile = _generate_jenkinsfile(with_docker=True, with_k8s=True)

        assert 'stage(\'Deploy\')' in jenkinsfile
        assert 'kubectl apply' in jenkinsfile
        assert 'withKubeConfig' in jenkinsfile

    def test_jenkinsfile_all_features(self):
        """Test Jenkinsfile with all features"""
        jenkinsfile = _generate_jenkinsfile(with_docker=True, with_k8s=True)

        assert 'Setup' in jenkinsfile
        assert 'Validate' in jenkinsfile
        assert 'Test' in jenkinsfile
        assert 'Build' in jenkinsfile
        assert 'Docker Build' in jenkinsfile
        assert 'Deploy' in jenkinsfile
        assert 'post {' in jenkinsfile
        assert 'always {' in jenkinsfile
