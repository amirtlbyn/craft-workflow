# Frontend Rewrite Tasks

This directory contains the comprehensive task list for rewriting craft-workflow to support frontend development. The tasks are organized by phase and component, following the structure outlined in `frontend-rewrite-plan.md` and `frontend-technical-spec.md`.

## Task Structure

Each task file follows the craft-workflow task template format with:
- **Spec reference** to the technical specification
- **Key identifier** for tracking (FSD, BTI, CDS, etc.)
- **Route** (all are `project` for this rewrite)
- **Checkpoint** command for validation
- **Session breakdown** with individual tasks
- **Gate requirements** for completion

## Phases Overview

### Phase 1: Foundation Layer
- **01-frontend-stack-detection.md**: React, Vue, Angular stack detection
- **02-build-tool-integration.md**: Vite, Webpack, bundle analysis integration

### Phase 2: Frontend Skills Development
- **01-component-design-skill.md**: Component design principles and patterns
- **02-state-management-skill.md**: State management patterns and optimization
- **03-styling-discipline-skill.md**: CSS methodologies and design systems

### Phase 3: Review Lenses Creation
- **01-component-review-lens.md**: Component validation and review criteria
- **02-accessibility-review-lens.md**: Accessibility compliance and testing

### Phase 4: Frontend Gates Implementation
- **01-component-gate-implementation.md**: Component validation gates

### Integration Tasks
- **01-craft-stack-integration.md**: Integration with existing craft-stack command

### Testing Framework
- **01-e2e-testing-framework.md**: End-to-end testing for all components

## Implementation Order

1. **Start with Phase 1** to establish the foundation
2. **Proceed to Phase 2** for skill development
3. **Move to Phase 3** for review system
4. **Implement Phase 4** for gate enforcement
5. **Complete Integration** tasks
6. **Validate with Testing** framework

## Task Keys Legend

- **FSD**: Frontend Stack Detection
- **BTI**: Build Tool Integration
- **CDS**: Component Design Skill
- **SMS**: State Management Skill
- **SDS**: Styling Discipline Skill
- **CRL**: Component Review Lens
- **ARL**: Accessibility Review Lens
- **CGT**: Component Gate Implementation
- **CSI**: craft-stack Integration
- **ETF**: End-to-End Testing Framework

## Usage

Each task can be executed as a craft-workflow project:
```bash
# Example: Start frontend stack detection project
bin/craft-spec new --route project --title "Frontend Stack Detection System"
# Follow the tasks in phase1/01-frontend-stack-detection.md
```

## Progress Tracking

Monitor progress through:
1. Task completion checkboxes in each file
2. Gate A validation (bin/craft-spec trace)
3. Gate B validation (reviewer feedback)
4. Checkpoint command execution

## Dependencies

- Phase 1 must complete before Phase 2
- Skills (Phase 2) needed before Lenses (Phase 3)
- Lenses (Phase 3) needed before Gates (Phase 4)
- All phases needed before Integration
- Testing validates all components

## Success Criteria

Each phase is complete when:
1. All tasks in the phase are checked
2. Gate A passes (tests, lint, format)
3. Gate B passes (review approved)
4. Checkpoint command executes successfully
5. Integration with existing system validated