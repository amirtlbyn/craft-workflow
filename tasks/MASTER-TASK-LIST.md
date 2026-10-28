# Master Task List - Frontend Rewrite

## Overview
Total Tasks: 10 in-scope project files · Estimated Sessions: 37 · Total Subtasks: ~350

## Phase 1: Foundation Layer (Month 1-2)

### 1. Frontend Stack Detection System
- **File**: `phase1/01-frontend-stack-detection.md`
- **Key**: FSD-1
- **Sessions**: 4
- **Subtasks**: 23
- **Status**: ✅ Done
- **Dependencies**: None

### 2. Build Tool Integration System
- **File**: `phase1/02-build-tool-integration.md`
- **Key**: BTI-1
- **Sessions**: 5
- **Subtasks**: 32
- **Status**: ✅ Done
- **Dependencies**: FSD-1 (partial)

## Phase 2: Frontend Skills Development (Month 3-4)

### 3. Component Design Skill
- **File**: `phase2/01-component-design-skill.md`
- **Key**: CDS-1
- **Sessions**: 5
- **Subtasks**: 36
- **Status**: ✅ Done
- **Dependencies**: FSD-1 complete

### 4. State Management Skill
- **File**: `phase2/02-state-management-skill.md`
- **Key**: SMS-1
- **Sessions**: 5
- **Subtasks**: 35
- **Status**: ✅ Done
- **Dependencies**: CDS-1 (partial)

### 5. Styling Discipline Skill
- **File**: `phase2/03-styling-discipline-skill.md`
- **Key**: SDS-1
- **Sessions**: 5
- **Subtasks**: 35
- **Status**: ✅ Done
- **Dependencies**: CDS-1 (partial)

## Phase 3: Review Lenses Creation (Month 5)

### 6. Component Review Lens
- **File**: `phase3/01-component-review-lens.md`
- **Key**: CRL-1
- **Sessions**: 5
- **Subtasks**: 35
- **Status**: ✅ Done
- **Dependencies**: CDS-1, SMS-1, SDS-1 complete

### 7. Accessibility Review Lens
- **File**: `phase3/02-accessibility-review-lens.md`
- **Key**: ARL-1
- **Sessions**: 5
- **Subtasks**: 35
- **Status**: ✅ Done
- **Dependencies**: CDS-1 complete

## Phase 4: Frontend Gates Implementation (Month 6)

### 8. Component Gate Implementation
- **File**: `phase4/01-component-gate-implementation.md`
- **Key**: CGT-1
- **Sessions**: 5
- **Subtasks**: 35
- **Status**: ⚠️ Done (scoped) — gate enforces 3 rules (no-component, listener-teardown, raw-hex-style); spec §5.2's verify_props_interface / verify_storybook_integration deferred to the component review lens
- **Dependencies**: CRL-1, ARL-1 complete

## Integration Phase

### 9. craft-stack Integration
- **File**: `integration/01-craft-stack-integration.md`
- **Key**: CSI-1
- **Sessions**: 5
- **Subtasks**: 34
- **Status**: ✅ Done
- **Dependencies**: All Phase 1-4 complete

## Testing & Validation

### 10. End-to-End Testing Framework
- **File**: `testing/01-e2e-testing-framework.md`
- **Key**: ETF-1
- **Sessions**: 6
- **Subtasks**: 42
- **Status**: ✅ Done
- **Dependencies**: CSI-1 complete

## Progress Tracking

### Current Status
```
Phase 1: 2/2 completed (100%)
Phase 2: 3/3 completed (100%)
Phase 3: 2/2 planned lenses completed (100%); performance/mobile lenses deferred
Phase 4: 1/1 planned gate completed (100%); bundle/accessibility gates deferred
Integration: 1/1 completed (100%)
Testing: 1/1 completed (100%)
Overall: 10/10 in-scope tasks completed (100%); Svelte/SolidJS/Qwik expansion deferred

Deferred (documented, not built): Lighthouse CI integration (BTI-5 T28),
frameworks→skills mapping (FSD-1 T4), gate prop/storybook verification (CGT-1),
bundle/accessibility gates, performance/mobile lenses
```

Note: the deferred expansion beyond the 10 in-scope task files covers
Svelte/SolidJS/Qwik support, as described in frontend-rewrite-plan.md: "Start
with React/Vue, expand based on demand." All 10 in-scope task files are done
and verified.

### Completion Criteria
- [x] Phase 1: Stack detection & build tools working
- [x] Phase 2: All frontend skills developed and tested
- [x] Phase 3: Component/accessibility lenses implemented; performance/mobile deferred
- [x] Phase 4: Component gate implemented; bundle/accessibility gates deferred
- [x] Integration: Seamless integration with craft-workflow
- [x] Testing: Comprehensive test coverage achieved

## Risk Assessment

### High Risk Tasks
1. **FSD-1**: Framework detection accuracy
2. **BTI-1**: Build tool compatibility
3. **CSI-1**: Backward compatibility maintenance

### Medium Risk Tasks
1. **CDS-1**: Component pattern completeness
2. **CRL-1**: Review lens effectiveness
3. **CGT-1**: Gate enforcement reliability

### Low Risk Tasks
1. **SMS-1**: State management patterns
2. **SDS-1**: Styling guidelines
3. **ARL-1**: Accessibility standards

## Success Metrics

### Technical Metrics
- [ ] 95% test coverage for all new code
- [ ] Zero regression in existing backend functionality
- [ ] All gates pass for sample frontend projects
- [ ] Integration tests pass for mixed stack projects

### Usability Metrics
- [ ] React, Vue, Angular detection working reliably
- [ ] Skills provide actionable guidance
- [ ] Lenses catch common frontend issues
- [ ] Gates provide clear failure feedback

### Performance Metrics
- [ ] Stack detection < 1 second
- [ ] Build analysis < 30 seconds
- [ ] No impact on existing backend workflow performance
- [ ] Memory usage within acceptable limits

## Next Steps

1. **Start Phase 1**: Begin with `phase1/01-frontend-stack-detection.md`
2. **Weekly Review**: Check progress against this master list
3. **Risk Mitigation**: Address high-risk tasks early
4. **Integration Testing**: Test each phase with existing system
5. **Documentation**: Update as features are completed
