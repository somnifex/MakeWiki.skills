# Core Data Contracts & Schemas

## 1. SemanticModel

```json
{
  "identity": {
    "name": "my-app",
    "version": "1.0.0",
    "description": "Short project description"
  },
  "installation": {
    "prerequisites": [{"name": "Node.js", "version_constraint": ">=18"}],
    "steps": [{"order": 1, "title": "Install", "commands": ["npm install"]}],
    "verify_command": "npm test"
  },
  "commands": [
    {
      "name": "my-app start",
      "description": "Start the service",
      "args": [{"name": "--port", "description": "Port number", "default": "3000"}]
    }
  ],
  "configuration": [
    {
      "name": "Server",
      "items": [{"key": "PORT", "description": "HTTP port", "default_value": "3000"}]
    }
  ]
}
```

## 2. EvidenceBundle

```json
{
  "detection": {
    "project_name": "my-app",
    "project_type": "node-cli",
    "confidence": 0.95
  },
  "total_facts": 12,
  "summary": {"command": 4, "config_key": 6, "path": 2},
  "commands_discovered": ["npm run build", "npm start"]
}
```