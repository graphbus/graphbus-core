import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from graphbus_core.config import BuildConfig
from graphbus_core.build.builder import build_project

config = BuildConfig(
    root_package="examples.news_summarizer.agents",
    output_dir="examples/news_summarizer/.graphbus"
)
config.llm_config = {'model': 'claude-sonnet-4-20250514', 'api_key': os.environ.get('ANTHROPIC_API_KEY')}

artifacts = build_project(config, enable_agents=os.environ.get('ANTHROPIC_API_KEY') is not None)
print(f"\n✅ Build complete: {artifacts.agents_count} agents, {artifacts.topics_count} topics")
