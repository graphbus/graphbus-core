"""
Tests for Kubernetes command
"""

import pytest
from pathlib import Path
from click.testing import CliRunner

from graphbus_cli.commands.k8s import (
    k8s, _generate_deployment, _generate_service,
    _generate_configmap, _generate_pvc, _generate_hpa, _generate_ingress
)


class TestK8sGenerate:
    """Test k8s generate command"""

    @pytest.fixture
    def runner(self):
        """Create CLI runner"""
        return CliRunner()

    def test_generate_basic_manifests(self, runner, tmp_path):
        """Test generating basic K8s manifests"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(k8s, ['generate'])
            assert result.exit_code == 0
            assert 'Generated deployment.yaml' in result.output
            assert 'Generated service.yaml' in result.output

            # Check files exist
            assert Path('k8s/deployment.yaml').exists()
            assert Path('k8s/service.yaml').exists()

            # Check deployment content
            deployment = Path('k8s/deployment.yaml').read_text()
            assert 'kind: Deployment' in deployment
            assert 'replicas: 3' in deployment
            assert 'image: graphbus-app:latest' in deployment

            # Check service content
            service = Path('k8s/service.yaml').read_text()
            assert 'kind: Service' in service
            assert 'type: ClusterIP' in service
            assert 'port: 8080' in service

    def test_generate_with_configmap(self, runner, tmp_path):
        """Test generating manifests with ConfigMap"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(k8s, ['generate', '--with-configmap'])
            assert result.exit_code == 0
            assert 'Generated configmap.yaml' in result.output

            configmap = Path('k8s/configmap.yaml').read_text()
            assert 'kind: ConfigMap' in configmap
            assert 'GRAPHBUS_ENV' in configmap

    def test_generate_with_pvc(self, runner, tmp_path):
        """Test generating manifests with PVC"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(k8s, ['generate', '--with-pvc'])
            assert result.exit_code == 0
            assert 'Generated pvc.yaml' in result.output

            pvc = Path('k8s/pvc.yaml').read_text()
            assert 'kind: PersistentVolumeClaim' in pvc
            assert 'ReadWriteOnce' in pvc
            assert '10Gi' in pvc

    def test_generate_with_autoscaler(self, runner, tmp_path):
        """Test generating manifests with HPA"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(k8s, ['generate', '--with-autoscaler'])
            assert result.exit_code == 0
            assert 'Generated hpa.yaml' in result.output

            hpa = Path('k8s/hpa.yaml').read_text()
            assert 'kind: HorizontalPodAutoscaler' in hpa
            assert 'minReplicas:' in hpa
            assert 'maxReplicas:' in hpa

    def test_generate_with_ingress(self, runner, tmp_path):
        """Test generating manifests with Ingress"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(k8s, ['generate', '--with-ingress'])
            assert result.exit_code == 0
            assert 'Generated ingress.yaml' in result.output

            ingress = Path('k8s/ingress.yaml').read_text()
            assert 'kind: Ingress' in ingress
            assert 'graphbus.example.com' in ingress

    def test_generate_custom_namespace(self, runner, tmp_path):
        """Test generating manifests with custom namespace"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(k8s, ['generate', '--namespace', 'production'])
            assert result.exit_code == 0

            deployment = Path('k8s/deployment.yaml').read_text()
            assert 'namespace: production' in deployment

    def test_generate_custom_replicas(self, runner, tmp_path):
        """Test generating manifests with custom replicas"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(k8s, ['generate', '--replicas', '5'])
            assert result.exit_code == 0

            deployment = Path('k8s/deployment.yaml').read_text()
            assert 'replicas: 5' in deployment

    def test_generate_custom_image(self, runner, tmp_path):
        """Test generating manifests with custom image"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(k8s, ['generate', '--image', 'my-registry/graphbus:v1.0'])
            assert result.exit_code == 0

            deployment = Path('k8s/deployment.yaml').read_text()
            assert 'image: my-registry/graphbus:v1.0' in deployment

    def test_generate_custom_output_dir(self, runner, tmp_path):
        """Test generating manifests to custom directory"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(k8s, ['generate', '--output-dir', 'manifests'])
            assert result.exit_code == 0

            assert Path('manifests/deployment.yaml').exists()
            assert Path('manifests/service.yaml').exists()

    def test_generate_all_options(self, runner, tmp_path):
        """Test generating manifests with all options"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(k8s, [
                'generate',
                '--namespace', 'prod',
                '--replicas', '5',
                '--image', 'custom:v1',
                '--with-configmap',
                '--with-pvc',
                '--with-autoscaler',
                '--with-ingress'
            ])
            assert result.exit_code == 0
            assert Path('k8s/deployment.yaml').exists()
            assert Path('k8s/service.yaml').exists()
            assert Path('k8s/configmap.yaml').exists()
            assert Path('k8s/pvc.yaml').exists()
            assert Path('k8s/hpa.yaml').exists()
            assert Path('k8s/ingress.yaml').exists()


class TestK8sManifestGeneration:
    """Test K8s manifest generation functions"""

    def test_generate_deployment_basic(self):
        """Test basic deployment generation"""
        deployment = _generate_deployment(
            namespace='default',
            replicas=3,
            image='graphbus-app:latest',
            with_configmap=False,
            with_pvc=False
        )

        assert 'apiVersion: apps/v1' in deployment
        assert 'kind: Deployment' in deployment
        assert 'namespace: default' in deployment
        assert 'replicas: 3' in deployment
        assert 'image: graphbus-app:latest' in deployment
        assert 'containerPort: 8080' in deployment
        assert 'livenessProbe:' in deployment
        assert 'readinessProbe:' in deployment

    def test_generate_deployment_with_configmap(self):
        """Test deployment with ConfigMap"""
        deployment = _generate_deployment(
            namespace='default',
            replicas=3,
            image='graphbus-app:latest',
            with_configmap=True,
            with_pvc=False
        )

        assert 'envFrom:' in deployment
        assert 'configMapRef:' in deployment
        assert 'graphbus-config' in deployment

    def test_generate_deployment_with_pvc(self):
        """Test deployment with PVC"""
        deployment = _generate_deployment(
            namespace='default',
            replicas=3,
            image='graphbus-app:latest',
            with_configmap=False,
            with_pvc=True
        )

        assert 'volumeMounts:' in deployment
        assert 'graphbus-state' in deployment
        assert '/app/state' in deployment
        assert 'volumes:' in deployment
        assert 'persistentVolumeClaim:' in deployment

    def test_generate_service(self):
        """Test service generation"""
        service = _generate_service(namespace='production')

        assert 'apiVersion: v1' in service
        assert 'kind: Service' in service
        assert 'namespace: production' in service
        assert 'type: ClusterIP' in service
        assert 'port: 8080' in service
        assert 'targetPort: 8080' in service

    def test_generate_configmap(self):
        """Test ConfigMap generation"""
        configmap = _generate_configmap(namespace='staging')

        assert 'apiVersion: v1' in configmap
        assert 'kind: ConfigMap' in configmap
        assert 'namespace: staging' in configmap
        assert 'GRAPHBUS_ENV' in configmap
        assert 'GRAPHBUS_LOG_LEVEL' in configmap

    def test_generate_pvc(self):
        """Test PVC generation"""
        pvc = _generate_pvc(namespace='default')

        assert 'apiVersion: v1' in pvc
        assert 'kind: PersistentVolumeClaim' in pvc
        assert 'namespace: default' in pvc
        assert 'ReadWriteOnce' in pvc
        assert '10Gi' in pvc

    def test_generate_hpa(self):
        """Test HPA generation"""
        hpa = _generate_hpa(namespace='default', replicas=3)

        assert 'apiVersion: autoscaling/v2' in hpa
        assert 'kind: HorizontalPodAutoscaler' in hpa
        assert 'namespace: default' in hpa
        assert 'minReplicas: 3' in hpa
        assert 'maxReplicas: 9' in hpa  # 3 * 3
        assert 'averageUtilization: 70' in hpa

    def test_generate_ingress(self):
        """Test Ingress generation"""
        ingress = _generate_ingress(namespace='default')

        assert 'apiVersion: networking.k8s.io/v1' in ingress
        assert 'kind: Ingress' in ingress
        assert 'namespace: default' in ingress
        assert 'graphbus.example.com' in ingress
        assert 'graphbus-service' in ingress
