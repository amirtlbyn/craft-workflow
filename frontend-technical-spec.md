# Frontend Technical Specification for Craft-Workflow Rewrite

## 1. Directory Structure Extension

### New Directories
```
frontend/
├── stacks/
│   ├── react/
│   │   ├── stack.json
│   │   ├── lenses.md
│   │   └── standards/
│   ├── vue/
│   │   ├── stack.json
│   │   ├── lenses.md
│   │   └── standards/
│   └── nuxt/
│       ├── stack.json
│       ├── lenses.md
│       └── standards/
├── skills/
│   ├── component-design/
│   │   ├── SKILL.md
│   │   └── references/
│   ├── state-management/
│   │   ├── SKILL.md
│   │   └── references/
│   ├── frontend-testing/
│   │   ├── SKILL.md
│   │   └── references/
│   └── styling-discipline/
│       ├── SKILL.md
│       └── references/
├── hooks/
│   ├── bundle-analyzer.py
│   ├── accessibility-check.py
│   └── component-gate.py
└── standards/
    ├── component_design_standards.ai.md
    ├── frontend_performance_standards.ai.md
    └── accessibility_standards.ai.md
```

## 2. Frontend Stack Configuration

### React Stack Configuration (`stacks/react/stack.json`)
```json
{
  "id": "react",
  "label": "React",
  "emoji": "⚛️",
  "language": "javascript",
  "priority": 80,
  "detect": {
    "any_file": ["package.json"],
    "any_contains": [
      {
        "files": ["package.json"],
        "pattern": "\"react\"\\s*:"
      }
    ]
  },
  "frameworks": {
    "next": {
      "detect": ["next.config.js", "next.config.mjs"],
      "skills": ["next-practices", "ssr-optimization"]
    },
    "remix": {
      "detect": ["remix.config.js"],
      "skills": ["remix-practices", "loader-actions"]
    },
    "vite": {
      "detect": ["vite.config.js", "vite.config.ts"],
      "skills": ["vite-optimization"]
    }
  },
  "source_extensions": [".js", ".jsx", ".ts", ".tsx"],
  "tests": {
    "globs": [
      "**/*.test.{js,jsx,ts,tsx}",
      "**/*.spec.{js,jsx,ts,tsx}",
      "__tests__/**/*",
      "tests/**/*"
    ],
    "extensions": [".js", ".jsx", ".ts", ".tsx"],
    "id_rule": "Put the criterion ID in the test description: test('WDL-2: should ...', () => {})"
  },
  "checks": {
    "bundle": [
      {
        "run": "npx webpack-bundle-analyzer --mode production",
        "when": "webpack detected"
      },
      {
        "run": "npx vite-bundle-analyzer",
        "when": "vite detected"
      }
    ],
    "performance": [
      {
        "run": "npx lighthouse-ci --collect.url=http://localhost:3000"
      }
    ],
    "accessibility": [
      {
        "run": "npx axe-core --dir ./src"
      }
    ],
    "component": [
      {
        "run": "npx chromatic --project-token=${CHROMATIC_TOKEN}",
        "when": "storybook detected"
      }
    ]
  },
  "skills": [
    "component-design",
    "state-management",
    "frontend-testing",
    "styling-discipline"
  ],
  "standards": [
    "component_design_standards",
    "frontend_performance_standards",
    "accessibility_standards"
  ],
  "lenses": "stacks/react/lenses.md"
}
```

## 3. Frontend Skills Specification

### 3.1 Component Design Skill (`skills/component-design/SKILL.md`)
```markdown
---
name: component-design
description: "Design and implement React/Vue/Nuxt components following best practices. Load before creating any new component."
---

# Component Design Principles

## 1. Props Design
- Use TypeScript/PropTypes for all props
- Provide sensible defaults
- Document prop usage with JSDoc
- Follow naming conventions (camelCase for props)

## 2. Component Composition
- Prefer composition over inheritance
- Use React Context for deep prop drilling
- Implement render props or hooks for flexibility
- Follow the Single Responsibility Principle

## 3. State Management
- Lift state up when shared
- Use local state for component-specific data
- Implement custom hooks for reusable logic
- Consider performance implications

## 4. Performance Optimization
- Memoize expensive computations
- Implement proper dependency arrays
- Use React.memo() for pure components
- Implement virtualization for large lists

## 5. Accessibility
- Include ARIA attributes
- Ensure keyboard navigation
- Provide proper focus management
- Support screen readers
```

### 3.2 State Management Skill (`skills/state-management/SKILL.md`)
```markdown
---
name: state-management
description: "Manage application state efficiently using appropriate patterns and libraries."
---

# State Management Guidelines

## 1. State Selection
- **Local State**: useState, useReducer (component-specific)
- **Global State**: Zustand, Jotai, Redux Toolkit
- **Server State**: TanStack Query, SWR, Apollo
- **URL State**: React Router, useSearchParams

## 2. State Patterns
- Keep state as close to usage as possible
- Derive state when possible
- Normalize nested state
- Implement optimistic updates

## 3. Performance Considerations
- Implement state slicing
- Use selectors for derived state
- Memoize selectors with reselect
- Batch state updates

## 4. Testing State
- Test state transitions
- Mock server state
- Test side effects
- Validate state persistence
```

## 4. Frontend Review Lenses

### 4.1 Component Lens (`stacks/react/lenses.md` - Section)
```markdown
## Component Lens

Checklist:
- [ ] Props are properly typed/validated
- [ ] Component is properly memoized when needed
- [ ] Event handlers are debounced/throttled appropriately
- [ ] Component follows composition patterns
- [ ] Error boundaries are implemented for critical components
- [ ] Loading states are handled gracefully
- [ ] Component is testable (injected dependencies)

Severity Ceiling: High
Confidence Threshold: 0.7

### Stack-Specific Notes

#### React
- Use React.memo() for pure components
- Implement useCallback for event handlers
- Use useMemo for expensive calculations
- Follow hooks rules (no conditional hooks)

#### Vue
- Use computed properties for derived state
- Implement watchers appropriately
- Use provide/inject for deep component trees
- Follow composition API patterns
```

### 4.2 Accessibility Lens
```markdown
## Accessibility Lens

Checklist:
- [ ] All interactive elements are keyboard accessible
- [ ] ARIA attributes are used appropriately
- [ ] Color contrast meets WCAG AA standards
- [ ] Focus indicators are visible
- [ ] Screen reader announcements are proper
- [ ] Form labels are associated with inputs
- [ ] Error messages are accessible

Severity Ceiling: Critical
Confidence Threshold: 0.8

### Testing Commands
```bash
# Run automated accessibility tests
npx axe-core --dir ./src

# Check color contrast
npx color-contrast-checker ./src

# Test keyboard navigation
# Manual testing required
```
```

## 5. Frontend-Specific Hooks

### 5.1 Bundle Analyzer Hook (`hooks/bundle-analyzer.py`)
```python
#!/usr/bin/env python3
"""
Hook: PreToolUse for Write/Edit operations on frontend files
Checks bundle size impact of changes
"""

import json
import subprocess
import sys
from pathlib import Path

def analyze_bundle_impact(changed_files):
    """Analyze the impact of changed files on bundle size"""
    
    # Run bundle analysis if package.json changed
    if any('package.json' in str(f) for f in changed_files):
        return run_bundle_analysis()
    
    # Check for new dependencies
    if has_new_dependencies():
        return check_dependency_size()
    
    return {"allowed": True, "message": "Bundle impact within limits"}

def run_bundle_analysis():
    """Run webpack-bundle-analyzer or equivalent"""
    try:
        result = subprocess.run(
            ["npx", "webpack-bundle-analyzer", "--mode", "production", "--json"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            analysis = json.loads(result.stdout)
            if analysis["totalSize"] > 2 * 1024 * 1024:  # 2MB threshold
                return {
                    "allowed": False,
                    "message": f"Bundle size exceeds threshold: {analysis['totalSize']/1024/1024:.1f}MB"
                }
    
    except subprocess.TimeoutExpired:
        pass
    
    return {"allowed": True, "message": "Bundle analysis passed"}
```

### 5.2 Component Gate Hook (`hooks/component-gate.py`)
```python
#!/usr/bin/env python3
"""
Hook: Stop event for component changes
Verifies component meets design system requirements
"""

def verify_component_gate(component_path, spec):
    """Verify component meets all gates"""
    
    gates = [
        verify_props_interface(component_path, spec),
        verify_storybook_integration(component_path),
        verify_accessibility(component_path),
        verify_performance(component_path)
    ]
    
    failed_gates = [g for g in gates if not g["passed"]]
    
    if failed_gates:
        return {
            "passed": False,
            "failed_gates": failed_gates,
            "message": f"Component failed {len(failed_gates)} gate(s)"
        }
    
    return {"passed": True, "message": "All component gates passed"}

def verify_storybook_integration(component_path):
    """Check if component has Storybook stories"""
    story_path = component_path.with_suffix('.stories.jsx')
    
    if not story_path.exists():
        return {
            "passed": False,
            "gate": "storybook",
            "message": "Component missing Storybook stories"
        }
    
    return {"passed": True, "gate": "storybook"}
```

## 6. Testing Framework Integration

### 6.1 Test Configuration Detection
```python
def detect_testing_framework():
    """Detect which testing framework is in use"""
    
    configs = {
        "jest": ["jest.config.js", "jest.config.ts"],
        "vitest": ["vitest.config.js", "vitest.config.ts"],
        "cypress": ["cypress.config.js", "cypress.config.ts"],
        "playwright": ["playwright.config.js", "playwright.config.ts"]
    }
    
    for framework, config_files in configs.items():
        for config_file in config_files:
            if Path(config_file).exists():
                return framework
    
    # Check package.json for testing dependencies
    package_json = Path("package.json")
    if package_json.exists():
        with open(package_json) as f:
            data = json.load(f)
            
            deps = data.get("dependencies", {})
            dev_deps = data.get("devDependencies", {})
            all_deps = {**deps, **dev_deps}
            
            if "@testing-library/react" in all_deps:
                return "react-testing-library"
            elif "@vue/test-utils" in all_deps:
                return "vue-test-utils"
    
    return "unknown"
```

### 6.2 Test Runner Configuration
```json
{
  "test_runners": {
    "jest": {
      "unit": "jest --coverage",
      "component": "jest --testPathPattern=.*\\.(test|spec)\\.(js|jsx|ts|tsx)$",
      "coverage_threshold": 80
    },
    "vitest": {
      "unit": "vitest run --coverage",
      "component": "vitest run --dir=src/components",
      "coverage_threshold": 80
    },
    "cypress": {
      "e2e": "cypress run",
      "component": "cypress run --component"
    }
  }
}
```

## 7. Performance Monitoring

### 7.1 Performance Gate Configuration
```json
{
  "performance_gates": {
    "bundle_size": {
      "warning": 500000,  # 500KB
      "error": 2000000,   # 2MB
      "checks": ["main", "vendor", "runtime"]
    },
    "first_contentful_paint": {
      "warning": 2000,    # 2 seconds
      "error": 4000       # 4 seconds
    },
    "largest_contentful_paint": {
      "warning": 2500,    # 2.5 seconds
      "error": 4000       # 4 seconds
    },
    "cumulative_layout_shift": {
      "warning": 0.1,
      "error": 0.25
    }
  }
}
```

### 7.2 Performance Check Command
```bash
# Integrated performance check
bin/craft-check -- npx lighthouse-ci \
  --collect.url=http://localhost:3000 \
  --collect.settings.preset=desktop \
  --assert.bundle=500KB \
  --assert.lcp=2500ms \
  --output=json
```

## 8. Integration Points with Existing System

### 8.1 Modified Workflow Configuration
```markdown
## 9. Frontend Stacks

| Stack | Detected by | Tests name the ID in | Bundle Gate | Performance Gate |
|---|---|---|---|---|
| ⚛️ React | `package.json` contains `react` | test description: `test('WDL-3: ...')` | §12 | §13 |
| 🖖 Vue | `package.json` contains `vue` | test description: `it('WDL-3: ...')` | §12 | §13 |
| 🟩 Nuxt | `package.json` contains `nuxt` | test description: `it('WDL-3: ...')` | §12 | §13 |
| ⚡ Svelte | `package.json` contains `svelte` | test description | §12 | §13 |

## 12. Bundle Gate

| Check | Runs when | Command |
|---|---|---|
| Bundle size | Any frontend source change | `npx webpack-bundle-analyzer --mode production --json` |
| Asset optimization | Image/asset changes | `npx imagemin-cli` |
| Code splitting | Route/component changes | `bin/craft-check -- npx analyze-bundle-splitting` |

## 13. Performance Gate

| Check | Runs when | Command |
|---|---|---|
| Lighthouse audit | UI/component changes | `npx lighthouse-ci --collect.url=http://localhost:3000` |
| Bundle performance | Dependency changes | `npx speed-measure-webpack-plugin` |
| Runtime performance | State management changes | Chrome DevTools audit |
```

## 9. Migration and Compatibility

### 9.1 Feature Flags
```bash
# Enable frontend features gradually
export CRAFT_FRONTEND=react,performance
export CRAFT_FRONTEND_BUNDLE_ANALYSIS=true
export CRAFT_FRONTEND_ACCESSIBILITY=true
```

### 9.2 Backward Compatibility
- Existing backend stacks continue to work unchanged
- Frontend features are opt-in via configuration
- Mixed projects (fullstack) supported
- Gradual migration path for existing users

## 10. Development Roadmap

### Phase 1: MVP (Weeks 1-4)
- React stack detection
- Basic component skill
- Bundle size analysis
- Integration with existing craft command

### Phase 2: Enhanced Features (Weeks 5-8)
- Vue and Nuxt support
- Performance gates
- Accessibility lens
- Component testing integration

### Phase 3: Advanced Features (Weeks 9-12)
- Design system integration
- Visual regression testing
- E2E testing framework
- Mobile/PWA optimization

### Phase 4: Polish (Weeks 13-16)
- Documentation
- Performance optimization
- Community plugins
- Production readiness

This technical specification provides a detailed blueprint for extending craft-workflow to support frontend development while maintaining compatibility with the existing backend-focused system.