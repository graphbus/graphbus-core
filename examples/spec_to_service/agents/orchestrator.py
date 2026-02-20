"""
OrchestratorAgent - Coordinates the full spec-to-service pipeline.
"""

import os

from graphbus_core import GraphBusNode, schema_method, depends_on

from .spec_parser import SpecParserAgent
from .router import RouterAgent
from .model import ModelAgent
from .test_writer import TestAgent


@depends_on("RouterAgent", "ModelAgent", "TestAgent")
class OrchestratorAgent(GraphBusNode):
    SYSTEM_PROMPT = "You coordinate the full spec-to-service pipeline."

    @schema_method(
        input_schema={"spec": str, "service_name": str},
        output_schema={"output_dir": str, "files_written": list}
    )
    def build_service(self, spec: str, service_name: str) -> dict:
        """Run the full spec-to-service pipeline and write output files."""
        if not isinstance(spec, str) or not spec.strip():
            raise ValueError("'spec' must be a non-empty string")
        if not isinstance(service_name, str) or not service_name.strip():
            raise ValueError("'service_name' must be a non-empty string")

        # Step 1 — Parse the spec
        parser = SpecParserAgent()
        parsed = parser.parse_spec(spec)
        endpoints = parsed['endpoints']
        models = parsed['models']
        auth_required = parsed['auth_required']

        print(f"[OrchestratorAgent] Parsed spec: {len(endpoints)} endpoints, "
              f"{len(models)} models, auth={auth_required}")

        # Step 2 — Generate code (router + models in parallel in concept)
        router_agent = RouterAgent()
        router_result = router_agent.generate_router(endpoints, service_name)
        router_code = router_result['router_code']

        model_agent = ModelAgent()
        model_result = model_agent.generate_models(models)
        models_code = model_result['models_code']

        # Step 3 — Generate tests
        test_agent = TestAgent()
        test_result = test_agent.generate_tests(endpoints, service_name)
        test_code = test_result['test_code']

        # Step 4 — Generate main.py entry point
        main_code = self._generate_main(service_name)

        # Step 5 — Write output files
        output_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'output'
        )
        os.makedirs(output_dir, exist_ok=True)

        files = {
            'models.py': models_code,
            'router.py': router_code,
            'test_router.py': test_code,
            'main.py': main_code,
        }

        files_written = []
        for filename, content in files.items():
            filepath = os.path.join(output_dir, filename)
            with open(filepath, 'w') as f:
                f.write(content)
            files_written.append(filepath)
            print(f"[OrchestratorAgent] Wrote {filepath}")

        return {
            "output_dir": output_dir,
            "files_written": files_written,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_main(service_name: str) -> str:
        """Generate a main.py FastAPI app entry point."""
        return '\n'.join([
            '"""',
            f'{service_name} - FastAPI application entry point',
            '"""',
            '',
            'from fastapi import FastAPI',
            '',
            'from router import router',
            '',
            f'app = FastAPI(title="{service_name}")',
            'app.include_router(router)',
            '',
            '',
            'if __name__ == "__main__":',
            '    import uvicorn',
            '    uvicorn.run(app, host="0.0.0.0", port=8000)',
            '',
        ])
