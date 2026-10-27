# Frontend Developer Rewrite Plan for Craft-Workflow

## Executive Summary

Craft-workflow is a sophisticated spec-driven, cost-routed engineering workflow designed for backend stacks (Django, FastAPI, Go, Java, Node, PHP). It provides a structured process for development with three cost routes, spec gates, and automated review systems. This document outlines a plan to adapt this workflow for frontend development while maintaining its core principles.

## Current Architecture Analysis

### Core Components
1. **Three Cost Routes**
   - `quick`: Minor fixes, no spec/reviewer
   - `task`: Single merge request with spec
   - `project`: Multiple sessions with design phase

2. **Spec-Driven Workflow**
   - `spec.md` as source of truth
   - Developer approval gates
   - SHA-256 bound approvals for security

3. **Review System**
   - Single reviewer with multiple lenses
   - `deep-reviewer` for high-risk changes
   - Lens-based review (spec, style, logic, security, query)

4. **Stack Detection System**
   - Automated detection of backend frameworks
   - Stack-specific skills and checks
   - Language-specific test ID patterns

5. **Enforcement Hooks**
   - Spec gate enforcement
   - Human-owned file protection
   - Gate verification on completion

## Frontend-Specific Challenges

### 1. **Framework Diversity**
- React (with Next.js, Remix, Vite)
- Vue (with Nuxt, Vite)
- Angular
- Svelte/SvelteKit
- SolidJS
- Qwik

### 2. **Build Tool Ecosystem**
- Webpack, Vite, Parcel, Turbopack
- Multiple bundler configurations
- Dev server variations

### 3. **Testing Landscape**
- Component testing (React Testing Library, Vue Test Utils)
- E2E testing (Cypress, Playwright)
- Unit testing (Jest, Vitest)
- Visual testing (Storybook, Chromatic)

### 4. **State Management Patterns**
- Redux, Zustand, Jotai, Recoil
- Context API, Signals
- Server state (TanStack Query, SWR, Apollo)

### 5. **Styling Approaches**
- CSS-in-JS (Styled Components, Emotion)
- Utility CSS (Tailwind, UnoCSS)
- CSS Modules, SCSS/Less
- Design systems (MUI, Chakra, Ant Design)

## Rewrite Architecture

### Phase 1: Foundation Layer

#### 1.1 **Frontend Stack Detection**
```json
{
  "react": {
    "detect": ["package.json contains react"],
    "frameworks": ["next", "remix", "vite", "create-react-app"],
    "skills": ["react-practices", "component-design"],
    "testing": {
      "unit": "jest/vitest",
      "component": "react-testing-library",
      "e2e": "cypress/playwright"
    }
  },
  "vue": {
    "detect": ["package.json contains vue"],
    "frameworks": ["nuxt", "vite", "vue-cli"],
    "skills": ["vue-practices", "composition-api"],
    "testing": ["vitest", "vue-test-utils"]
  }
}
```

#### 1.2 **Build Tool Detection**
```python
def detect_build_tool():
    if "vite.config" exists: return "vite"
    if "next.config" exists: return "nextjs"
    if "webpack.config" exists: return "webpack"
    if "turbopack.config" exists: return "turbopack"
    return "unknown"
```

### Phase 2: Frontend-Specific Skills

#### 2.1 **Component Design Skill**
- Atomic design principles
- Props interface design
- Composition patterns
- Reusability guidelines

#### 2.2 **State Management Skill**
- State selection patterns
- Side effect management
- Performance optimization
- Server state synchronization

#### 2.3 **Styling Discipline Skill**
- CSS methodology selection
- Design system integration
- Responsive design patterns
- Accessibility compliance

#### 2.4 **Frontend Testing Skill**
- Component testing strategies
- Mocking approaches
- E2E test structuring
- Visual regression testing

### Phase 3: Frontend Review Lenses

#### 3.1 **Component Lens**
- Props validation and defaults
- Event handling patterns
- Lifecycle management
- Performance considerations

#### 3.2 **Accessibility Lens**
- ARIA attributes
- Keyboard navigation
- Screen reader compatibility
- Color contrast ratios

#### 3.3 **Performance Lens**
- Bundle size analysis
- Rendering optimization
- Network request patterns
- Memory leak detection

#### 3.4 **Mobile Lens**
- Responsive design compliance
- Touch interaction patterns
- Mobile performance metrics
- PWA capabilities

### Phase 4: Frontend-Specific Gates

#### 4.1 **Component Gate**
- Props interface validation
- Storybook/Chromatic integration
- Component documentation
- Design system compliance

#### 4.2 **Bundle Gate**
- Bundle size thresholds
- Code splitting verification
- Tree shaking validation
- Asset optimization

#### 4.3 **Accessibility Gate**
- WCAG compliance checks
- Automated a11y testing
- Manual review requirements
- Assistive technology testing

## Implementation Roadmap

### Month 1-2: Core Infrastructure
1. **Frontend stack detection system**
2. **Build tool integration**
3. **Basic frontend skills (component, styling)**
4. **Initial review lenses**

### Month 3-4: Advanced Features
1. **State management patterns**
2. **Performance optimization tools**
3. **Testing framework integration**
4. **Accessibility compliance system**

### Month 5-6: Polish & Integration
1. **Design system integration**
2. **Visual regression testing**
3. **Bundle analysis tools**
4. **Mobile/PWA support**

## Technical Considerations

### 1. **Plugin System Extension**
```typescript
interface FrontendStack {
  id: string;
  label: string;
  emoji: string;
  framework?: string;
  skills: string[];
  checks: FrontendChecks;
  testing: TestingConfig;
}

interface FrontendChecks {
  bundle: BundleCheck[];
  performance: PerformanceCheck[];
  accessibility: AccessibilityCheck[];
  component: ComponentCheck[];
}
```

### 2. **Build Analysis Integration**
```python
class BundleAnalyzer:
    def analyze(self, build_output):
        # Analyze bundle size
        # Check code splitting
        # Validate tree shaking
        # Report optimization opportunities
```

### 3. **Component Testing Framework**
```javascript
class ComponentTestValidator:
    validateComponent(componentPath, spec) {
        // Check props interface
        // Validate event handlers
        // Verify accessibility
        // Check performance patterns
    }
```

## Migration Strategy

### 1. **Backward Compatibility**
- Maintain existing backend stack support
- Gradual frontend feature introduction
- Configurable feature flags

### 2. **Progressive Enhancement**
- Start with React/Next.js support
- Expand to Vue, Angular, Svelte
- Add framework-specific optimizations

### 3. **Community Integration**
- Open source contributions
- Framework maintainer collaboration
- Plugin ecosystem development

## Success Metrics

### 1. **Adoption Metrics**
- Number of frontend projects using craft-workflow
- Framework coverage percentage
- Community plugin contributions

### 2. **Quality Metrics**
- Reduction in accessibility violations
- Improvement in bundle size
- Decrease in performance issues
- Increase in test coverage

### 3. **Productivity Metrics**
- Time saved in code review
- Reduction in rework
- Increase in developer satisfaction
- Improvement in onboarding speed

## Risks and Mitigations

### 1. **Framework Fragmentation Risk**
- **Risk**: Too many frameworks to support effectively
- **Mitigation**: Start with React/Vue, expand based on demand

### 2. **Performance Overhead Risk**
- **Risk**: Build analysis adds significant time
- **Mitigation**: Implement caching, parallel execution

### 3. **Adoption Barrier Risk**
- **Risk**: Complex setup discourages use
- **Mitigation**: Provide starter templates, clear documentation

## Conclusion

The craft-workflow rewrite for frontend development presents an opportunity to bring structured, spec-driven development to the frontend ecosystem. By adapting the proven backend workflow patterns to frontend-specific challenges, we can create a powerful tool that improves code quality, reduces review time, and ensures consistency across frontend projects.

The phased approach allows for iterative development and validation, ensuring each component delivers value before proceeding to the next phase. The modular architecture supports extensibility, allowing the community to contribute additional framework support and features over time.