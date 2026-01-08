"""
Configuration loader for AGI Engineer
Supports .agi-engineer.yml and .agi-engineer.yaml files
"""
import os
import yaml
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    'rules': {
        'enabled': ['F401', 'F541', 'W291', 'W292', 'E711', 'E712'],
        'disabled': [],
        'safe_only': True
    },
    'ai': {
        'enabled': True,
        'provider': 'groq',
        'max_files_to_analyze': 5,
        'custom_prompts': {}
    },
    'skip_patterns': [
        '__pycache__', '.git', '.venv', 'venv', 'node_modules',
        '*.min.js', '*.min.css', 'dist/', 'build/'
    ],
    'max_issues_per_run': 1000,
    'create_pr': False,
    'branch_prefix': 'agi-engineer/fixes',
    'commit_message_template': '🤖 AGI Engineer: Fixed {count} code issues'
}


class Config:
    """Configuration manager for AGI Engineer"""
    
    def __init__(self, repo_path: str = '.', config_file: Optional[str] = None):
        """
        Load configuration from file or use defaults
        
        Args:
            repo_path: Path to repository root
            config_file: Optional explicit config file path
        """
        self.repo_path = repo_path
        self.config = DEFAULT_CONFIG.copy()
        
        # Try to load config file
        config_path = self._find_config_file(config_file)
        if config_path:
            self._load_config(config_path)
        else:
            logger.info("No config file found, using defaults")
    
    def _find_config_file(self, explicit_path: Optional[str] = None) -> Optional[str]:
        """Find configuration file"""
        if explicit_path:
            if os.path.exists(explicit_path):
                return explicit_path
            else:
                logger.warning(f"Config file not found: {explicit_path}")
                return None
        
        # Look for config in repo root
        for filename in ['.agi-engineer.yml', '.agi-engineer.yaml', 'agi-engineer.yml']:
            path = os.path.join(self.repo_path, filename)
            if os.path.exists(path):
                logger.info(f"Found config file: {path}")
                return path
        
        return None
    
    def _load_config(self, config_path: str):
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                user_config = yaml.safe_load(f) or {}
            
            # Merge with defaults (user config overrides defaults)
            self._merge_config(user_config)
            logger.info(f"Loaded configuration from {config_path}")
            print(f"✅ Loaded config from {os.path.basename(config_path)}")
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in config file: {e}")
            print(f"⚠️  Invalid YAML in config file, using defaults")
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            print(f"⚠️  Failed to load config, using defaults")
    
    def _merge_config(self, user_config: Dict[str, Any]):
        """Recursively merge user config with defaults"""
        for key, value in user_config.items():
            if key in self.config and isinstance(self.config[key], dict) and isinstance(value, dict):
                self.config[key].update(value)
            else:
                self.config[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_enabled_rules(self) -> list:
        """Get list of enabled rules"""
        enabled = self.config['rules']['enabled']
        disabled = self.config['rules']['disabled']
        return [r for r in enabled if r not in disabled]
    
    def is_ai_enabled(self) -> bool:
        """Check if AI features are enabled"""
        return self.config['ai']['enabled']
    
    def should_skip(self, path: str) -> bool:
        """Check if path should be skipped"""
        import fnmatch
        
        patterns = self.config['skip_patterns']
        for pattern in patterns:
            if fnmatch.fnmatch(path, pattern) or pattern in path:
                return True
        return False
    
    def create_example_config(self, output_path: str = '.agi-engineer.yml'):
        """Create an example configuration file"""
        example = f"""# AGI Engineer Configuration
# Place this file in your repository root

rules:
  enabled:
    - F401  # Unused imports
    - F541  # Useless f-strings
    - W291  # Trailing whitespace
    - W292  # No newline at EOF
    - E711  # Comparison to None
  disabled: []
  safe_only: true  # Only auto-fix safe rules

ai:
  enabled: true
  provider: groq  # groq, together, openrouter, anthropic
  max_files_to_analyze: 5
  custom_prompts: {{}}

skip_patterns:
  - __pycache__
  - .git
  - .venv
  - venv
  - node_modules
  - "*.min.js"
  - "*.min.css"
  - dist/
  - build/

max_issues_per_run: 1000
create_pr: false
branch_prefix: "agi-engineer/fixes"
commit_message_template: "🤖 AGI Engineer: Fixed {{count}} code issues"
"""
        
        try:
            with open(output_path, 'w') as f:
                f.write(example)
            print(f"✅ Created example config: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create example config: {e}")
            print(f"❌ Failed to create example config: {e}")
            return False
