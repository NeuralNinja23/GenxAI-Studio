# ArborMind Authority Conflicts - Pre-Implementation Audit
**Date: 2025-12-28**  
**Critical: Must resolve before ArborMind implementation**

---

## Executive Summary

Found **4 major conflict areas** where existing FAST V2 logic could override or conflict with ArborMind's authority:

1. ✅ **Retry Logic** (orchestrator has its own retry mechanism)
2. ✅ **Execution Router** (makes RUN/HEAL/MUTATE decisions)
3. ✅ **Execution Policy** (defines per-step behavior)
4. ⚠️ **Supervision Layer** (Marcus can reject outputs)

**ArborMind Principle Violated**: *"The LLM must never decide correctness, terminate execution, override failure memory, or bypass semantic constraints. All such authority resides in the control layer."* (Appendix F.1)

---

## Conflict 1: Built-in Retry Logic

### Location
- `app/orchestration/fast_orchestrator.py` lines 420-462
- `app/orchestration/fast_orchestrator.py` lines 744-771

### Current Implementation
```python
# Lines 420-442
if self._should_retry_step(step):
    log("FAST-V2", f"🔄 Attempting retry for {step}")
    
    retry_success, retry_result = await self._retry_step_with_hardened_prompt(
        step, handler, context
    )
    
    if retry_success:
        log("FAST-V2", f"✅ Retry succeeded for {step}")
        result = retry_result
    else:
        log("FAST-V2", f"❌ Retry FAILED for {step}")
        # FATAL: halt workflow
```

### Function: `_should_retry_step()`
```python
# Line 796-802
def _should_retry_step(self, step_name: str) -> bool:
    """Decide if step should retry"""
    policy = get_execution_policy(step_name)
    
    return (
        policy.mode == ExecutionMode.ARTIFACT and
        policy.requires_output and
        policy.max_retries >= 1
    )
```

### Conflict with ArborMind
- **ArborMind's Control**: Attention + Repulsion determines retry
- **Current FAST V2**: Hard-coded policy determines retry
- **Problem**: Two separate retry authorities

### Solution
**Option A: ArborMind Replaces Retry Logic**
```python
# Remove _should_retry_step()
# Remove _retry_step_with_hardened_prompt()

# Replace with:
if arbormind_governor.should_retry(state, failure):
    healed_state = await arbormind_governor.heal(state, loss)
```

**Option B: ArborMind Wraps Retry Logic**
```python
# Keep existing retry but gate it through ArborMind
if arbormind_governor.allows_retry(step):
    if self._should_retry_step(step):
        # Existing retry logic
```

**Recommendation**: **Option A** - ArborMind has full authority

---

## Conflict 2: Execution Router

### Location
- `app/orchestration/fast_orchestrator.py` lines 175-205

### Current Implementation
```python
class ExecutionAction:
    """Actions the router can decide."""
    RUN_TOOL = "RUN_TOOL"
    STOP = "STOP"
    HEAL = "HEAL"      # ⚠️ Conflicts with ArborMind
    MUTATE = "MUTATE"  # ⚠️ Conflicts with ArborMind
    SKIP = "SKIP"

class ExecutionRouter:
    """Simple execution router - decides what to do for each step."""
    
    def decide(self, context: ExecutionContext, step_context: dict) -> ExecutionDecision:
        """Decide what action to take. For now, always run the tool."""
        # Simple implementation: always run the tool
        return ExecutionDecision(
            action=ExecutionAction.RUN_TOOL,
            reason=f"Executing step: {step_context.get('step', 'unknown')}"
        )
```

### Conflict with ArborMind
- **ArborMind's Control**: Governor decides RUN/HEAL/MUTATE via attention + loss
- **Current Router**: Has HEAL/MUTATE actions defined (not yet used)
- **Problem**: Router architecture anticipates decisions that ArborMind should make

### Solution
**Replace ExecutionRouter with ArborMindRouter**
```python
class ArborMindRouter:
    """ArborMind-controlled execution router"""
    
    def __init__(self, governor: ArborMindGovernor):
        self.governor = governor
        
    def decide(self, context: ExecutionContext, step_context: dict) -> ExecutionDecision:
        """
        Delegate all decisions to ArborMind Governor
        
        Governor computes:
        - Attention distribution
        - Validity check
        - Loss evaluation
        - Convergence check
        
        Returns: RUN_TOOL, STOP (Ω), or internal HEAL/MUTATE
        """
        return self.governor.get_next_action(context, step_context)
```

**Recommendation**: **Replace** ExecutionRouter with ArborMindRouter

---

## Conflict 3: Execution Policy

### Location
- `app/orchestration/fast_orchestrator.py` lines 74-131

### Current Implementation
```python
class ExecutionPolicy:
    """Execution policy for a step."""
    def __init__(self, mode: ExecutionMode, requires_output: bool,
                is_fatal: bool, max_retries: int):
        self.mode = mode
        self.requires_output = requires_output
        self.is_fatal = is_fatal
        self.max_retries = max_retries  # ⚠️ Conflicts with ArborMind

def get_execution_policy(step_name: str) -> ExecutionPolicy:
    """Get execution policy for a step."""
    ARTIFACT_STEPS = {
        "architecture": ExecutionPolicy(ExecutionMode.ARTIFACT, True, True, 1),
        "backend_models": ExecutionPolicy(ExecutionMode.ARTIFACT, True, True, 1),
        # ... more steps
    }
```

### Conflict with ArborMind
- **ArborMind's Control**: Semantic key (K) defines correctness constraints
- **Current Policy**: Hard-coded per-step retry counts and fatality
- **Problem**: Policy bypasses ArborMind's learning-based retry decisions

### Solution
**Option A: Keep Policy but Remove Retry/Fatality Fields**
```python
class ExecutionPolicy:
    """Execution policy - ONLY mode and output requirements"""
    def __init__(self, mode: ExecutionMode, requires_output: bool):
        self.mode = mode
        self.requires_output = requires_output
        # Removed: is_fatal, max_retries (ArborMind handles this)

# ArborMind decides fatality via:
# - Loss evaluation
# - Failure memory
# - Convergence check
```

**Option B: Merge Policy into Semantic Key (K)**
```python
# No ExecutionPolicy class
# All constraints defined in semantic_key.yaml:

semantic_key:
  architecture:
    mode: ARTIFACT
    requires_output: true
    invariants:
      - "Must define entity relationships"
      - "Must specify API contracts"
    correctness_modalities:
      - static
      - logical
```

**Recommendation**: **Option A** - Keep minimal policy, remove retry/fatality

---

## Conflict 4: Supervision Layer (Marcus)

### Location
- `app/supervision/supervisor.py`
- Integrated throughout orchestrator

### Current Implementation
```python
# Marcus can reject agent outputs
result = await supervised_agent_call(
    agent_name="derek",
    prompt=prompt,
    context=context
)

if result.rejection_reason:
    # Marcus rejected the output
    # Orchestrator decides what to do
```

### Conflict with ArborMind
- **ArborMind's Control**: Execution Oracle (multimodal) defines correctness
- **Marcus**: Another correctness authority
- **Problem**: Two sources of truth for "is output valid?"

### Solution
**Marcus becomes part of Execution Oracle**
```python
class ExecutionOracle:
    """Multimodal correctness evaluation"""
    
    async def evaluate(self, state: SoftwareState) -> float:
        static_loss = await self._static_analysis(state)
        logical_loss = await self._logical_validation(state)
        visual_loss = await self._visual_testing(state)
        marcus_loss = await self._marcus_review(state)  # ← Add Marcus here
        
        return (
            0.2 * static_loss +
            0.3 * logical_loss +
            0.2 * visual_loss +
            0.3 * marcus_loss  # Marcus is ONE modality
        )
        
    async def _marcus_review(self, state: SoftwareState) -> float:
        """Marcus as a validation modality, not a decision maker"""
        from app.supervision.supervisor import supervised_agent_call
        
        result = await supervised_agent_call(...)
        
        if result.rejection_reason:
            return 1.0  # Full loss
        else:
            return 0.0  # No loss
```

**Recommendation**: **Integrate** Marcus as Oracle modality, not separate authority

---

## Conflict 5: Token Budget Authority

### Location
- `app/orchestration/budget_manager.py`
- `app/orchestration/token_policy.py`

### Current Implementation
```python
class BudgetManager:
    def can_afford_step(self, step_name: str, is_retry: bool) -> bool:
        """Decide if we can afford to run step"""
        # Returns True/False - affects execution
```

### Conflict with ArborMind
- **ArborMind's Control**: Governor decides when to stop (Ω condition)
- **Budget Manager**: Can halt execution independently
- **Problem**: Budget might stop before convergence

### Solution
**Budget becomes Oracle modality (not decision maker)**
```python
# Instead of:
if not budget.can_afford_step(step):
    halt_workflow()  # ❌ Budget deciding

# Do this:
budget_constraint_violated = not budget.can_afford_step(step)

# Feed into ArborMind
loss = oracle.evaluate(state)
if budget_constraint_violated:
    loss += BUDGET_PENALTY  # Influences ArborMind's decision

# ArborMind decides whether to:
# - Continue (if close to convergence)
# - Mutate (try cheaper approach)
# - Stop (Ω condition + budget)
```

**Recommendation**: Budget informs ArborMind, doesn't override it

---

## Summary of Required Changes

### Priority 1: Remove Conflicting Authorities
- [ ] Remove/replace retry logic in orchestrator
- [ ] Remove HEAL/MUTATE from ExecutionRouter
- [ ] Remove max_retries/is_fatal from ExecutionPolicy
- [ ] Make budget non-blocking (informational only)

### Priority 2: Integrate Existing Components into ArborMind
- [ ] Marcus → ExecutionOracle modality
- [ ] Budget → Oracle constraint check
- [ ] Supervision → Logical validation component

### Priority 3: Create ArborMind Integration Points
- [ ] Replace ExecutionRouter with ArborMindRouter
- [ ] Add Governor.get_next_action() hook
- [ ] Add Oracle.evaluate() calls after each step
- [ ] Add convergence check in main loop

---

## Recommended Implementation Order

### Phase 0: Pre-Implementation Cleanup (Week 0)
**Before starting ArborMind implementation:**

1. **Simplify ExecutionPolicy**
   ```python
   # Remove these fields:
   - is_fatal
   - max_retries
   
   # Keep only:
   - mode (ARTIFACT/EVIDENCE/COGNITION)
   - requires_output (bool)
   ```

2. **Stub out retry logic**
   ```python
   def _should_retry_step(self, step_name: str) -> bool:
       # TODO: ArborMind will handle this
       return False  # Disable for now
   ```

3. **Make ExecutionRouter minimal**
   ```python
   class ExecutionRouter:
       def decide(self, context, step_context):
           # Simple pass-through until ArborMind Governor exists
           return ExecutionDecision(action=ExecutionAction.RUN_TOOL)
   ```

4. **Document all integration points**
   ```python
   # app/orchestration/fast_orchestrator.py
   
   # ARBORMIND INTEGRATION POINTS:
   # 1. Line 198: ExecutionRouter.decide() → will call Governor
   # 2. Line 420: Retry logic → will call Governor.heal()
   # 3. Line 347: ExecutionDecision → will check Ω condition
   ```

### Phase 1-6: ArborMind Implementation
Follow ARBORMIND_IMPLEMENTATION_PLAN.md

### Phase 7: Re-enable with ArborMind (Week 7)
1. Replace ExecutionRouter with ArborMindRouter
2. Wire Governor into orchestrator main loop
3. Replace retry logic with Governor.heal()
4. Add Ω convergence check

---

## Testing Plan

### Before ArborMind (Regression Tests)
- [ ] Existing workflows still complete
- [ ] No retry loops
- [ ] Budget enforcement still works
- [ ] Marcus supervision still runs

### After ArborMind (Integration Tests)
- [ ] ArborMind Governor controls execution
- [ ] Failure memory prevents repeats
- [ ] Convergence condition (Ω) works
- [ ] Marcus integrated as Oracle modality

---

## Open Questions

1. **Budget hard limit?**
   - Should budget EVER hard-stop, or always inform ArborMind?
   - Recommendation: Hard-stop only if budget.critical_threshold

2. **Marcus rejection = loss or halt?**
   - Current: Marcus rejection halts workflow
   - ArborMind: Marcus rejection adds to loss, Governor decides
   - Recommendation: Loss (let Governor decide)

3. **Backward compatibility?**
   - Should we support non-ArborMind mode?
   - Recommendation: No - ArborMind is always active once implemented

---

## References
- ArborMind Research: Appendix F.1 (Authority Separation)
- Current Orchestrator: `app/orchestration/fast_orchestrator.py`
- Implementation Plan: `ARBORMIND_IMPLEMENTATION_PLAN.md`
