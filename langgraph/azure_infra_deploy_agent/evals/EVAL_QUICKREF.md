# Parse User Input - Evaluation Quick Reference

## Files Created

1. **test_parse_user_input_eval.py** - Complete evaluation suite
2. **EVAL_GUIDE.md** - Detailed usage guide
3. **L11_ParseUserInput_Eval.ipynb** - Interactive notebook

## Quick Start

```bash
# Run all evaluations
python test_parse_user_input_eval.py
```

```python
# Or use in your code
from test_parse_user_input_eval import ParseEvaluationRunner, eval_llm

runner = ParseEvaluationRunner(eval_llm)
results = runner.run_outcome_based_tests()
```

## Three Evaluation Patterns

### 1. Outcome-Based ⚡ (Fast)
Direct comparison against expected outputs.

**When to use**: Regression testing, CI/CD pipelines
**Speed**: Fast
**Detail**: Low

```python
from test_parse_user_input_eval import OutcomeEvaluator

evaluator = OutcomeEvaluator()
result = evaluator.evaluate(user_input, parsed_output, expected)
# Returns: {matches: bool, score: 0-1, missing_fields: [], incorrect_fields: {}}
```

### 2. Rubric-Based 📊 (Detailed)
Multi-dimensional scoring with LLM-as-judge.

**When to use**: Quality improvement, manual review
**Speed**: Medium
**Detail**: High

```python
from test_parse_user_input_eval import RubricEvaluator, EVALUATION_RUBRIC, eval_llm

evaluator = RubricEvaluator(eval_llm, EVALUATION_RUBRIC)
result = evaluator.evaluate(user_input, parsed_output)
# Returns: {overall_score: 0-1, dimension_scores: {}, feedback: {}}
```

### 3. Reflection Pattern 🔄 (Iterative)
Self-improving through critique loops.

**When to use**: Production optimization, critical tasks
**Speed**: Slow
**Detail**: Very High

```python
from test_parse_user_input_eval import ParseReflector, eval_llm

reflector = ParseReflector(eval_llm, score_threshold=0.85)
result = reflector.parse_with_reflection(user_input, max_iterations=3)
# Returns: {final_output: {}, iterations: int, final_score: 0-1, evaluation_history: []}
```

## Evaluation Rubric (5 Dimensions)

| Dimension | Weight | What It Checks |
|-----------|--------|----------------|
| **required_fields** | 35% | resource_type, region, name present & correct |
| **optional_fields** | 25% | Optional fields from input correctly parsed |
| **defaults** | 15% | Default values set (e.g., resource_group) |
| **data_accuracy** | 15% | Valid Azure values (regions, SKUs, etc.) |
| **json_validity** | 10% | Output is valid, parseable JSON |

## Test Dataset (7 Cases)

✅ Basic storage (minimal fields)  
✅ Storage with SKU/performance  
✅ Key vault (full config)  
✅ App service (Linux + tier)  
✅ Storage with tags  
✅ Explicit resource group  
✅ Security settings  

## Score Interpretation

| Score | Quality | Action |
|-------|---------|--------|
| 0.90+ | ✅ Excellent | Production ready |
| 0.80-0.89 | 👍 Good | Minor tweaks |
| 0.70-0.79 | ⚠️ Moderate | Needs improvement |
| <0.70 | ❌ Low | Major revision needed |

## Common Issues & Fixes

### Issue: Low required_fields score
**Fix**: Make prompt more explicit about required fields
```python
# Add to prompt:
"REQUIRED: You MUST extract resource_type, region, and name from the user input."
```

### Issue: Low optional_fields score
**Fix**: Add examples to prompt
```python
# Add to prompt:
"Example: 'with zone redundancy' → zone_redundancy_enabled: true"
```

### Issue: Low defaults score
**Fix**: State defaults clearly
```python
# Add to prompt:
"If resource_group is not specified, use 'rg-deployment-test' as default."
```

### Issue: Low data_accuracy score
**Fix**: Add validation or use constrained values
```python
# Add post-processing:
VALID_REGIONS = ["East US", "West Europe", "UK South", ...]
if parsed["region"] not in VALID_REGIONS:
    # Find closest match or flag error
```

### Issue: Reflection not improving
**Fix**: Make feedback more actionable
- Increase LLM temperature slightly
- Use more capable model for refinement
- Provide specific examples in refinement prompt

## CI/CD Integration

```python
# Example GitHub Actions / Azure Pipelines
results = runner.run_outcome_based_tests()

if results['summary']['pass_rate'] < 0.8:
    print(f"❌ Tests failed: {results['summary']['pass_rate']:.1%}")
    exit(1)

print(f"✅ Tests passed: {results['summary']['pass_rate']:.1%}")
```

## Adding Custom Tests

```python
from test_parse_user_input_eval import TEST_CASES

TEST_CASES.append({
    "test_id": "my_test",
    "user_input": "Create storage account...",
    "expected": {
        "resource_type": "storage_account",
        "name": "mystore",
        # ... other fields
    },
    "description": "What this tests"
})
```

## Typical Workflow

```python
# 1. Quick regression check
outcome = runner.run_outcome_based_tests()
print(f"Pass rate: {outcome['summary']['pass_rate']:.1%}")

# 2. Investigate failures
for result in outcome['results']:
    if not result['passed']:
        # 3. Deep dive with rubric
        test_case = get_test_case(result['test_id'])
        rubric = runner.run_rubric_evaluation(test_case)
        
        # 4. Try improving with reflection
        if rubric['overall_score'] < 0.7:
            reflection = runner.run_reflection_test(test_case)
            print(f"Improved to: {reflection['final_score']:.2f}")
```

## Key Metrics to Track

1. **Pass Rate**: % of tests with exact matches
2. **Average Score**: Mean score across all tests
3. **Dimension Scores**: Which aspects need improvement
4. **Reflection Improvement**: How much reflection helps

## Configuration Options

```python
# Outcome-Based (no config needed)
evaluator = OutcomeEvaluator()

# Rubric-Based (can customize rubric)
custom_rubric = {
    "required_fields": {"weight": 0.5},  # Increase importance
    "optional_fields": {"weight": 0.3},
    # ...
}
evaluator = RubricEvaluator(eval_llm, custom_rubric)

# Reflection (customize threshold and iterations)
reflector = ParseReflector(
    eval_llm,
    score_threshold=0.90,  # Higher threshold
    max_iterations=5       # More iterations
)
```

## Resources

- **Full Guide**: EVAL_GUIDE.md
- **Interactive Notebook**: L11_ParseUserInput_Eval.ipynb
- **Test Suite**: test_parse_user_input_eval.py
- **Skill Reference**: .github/skills/SKILL.md

## One-Line Commands

```bash
# Run all tests
python test_parse_user_input_eval.py

# Open notebook
jupyter notebook L11_ParseUserInput_Eval.ipynb

# Run specific test
python -c "from test_parse_user_input_eval import *; runner = ParseEvaluationRunner(eval_llm); runner.run_rubric_evaluation(TEST_CASES[0])"
```

---

**Next Step**: Run `python test_parse_user_input_eval.py` to see all evaluations in action!
