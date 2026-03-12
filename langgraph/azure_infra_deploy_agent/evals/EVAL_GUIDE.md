# Evaluation Guide for parse_user_input

This guide shows how to use the comprehensive evaluation suite for the `parse_user_input` LLM method.

## Overview

The evaluation suite implements three patterns from the agentic-eval skill:

1. **Outcome-Based Evaluation** - Direct comparison against expected outputs
2. **Rubric-Based Evaluation** - Multi-dimensional scoring with LLM-as-judge
3. **Reflection Pattern** - Iterative self-improvement through critique

## Quick Start

### 1. Run All Evaluations

```python
from test_parse_user_input_eval import ParseEvaluationRunner, eval_llm

runner = ParseEvaluationRunner(eval_llm)

# Run all outcome-based tests
results = runner.run_outcome_based_tests()

# Run rubric evaluation on specific case
from test_parse_user_input_eval import TEST_CASES
rubric_results = runner.run_rubric_evaluation(TEST_CASES[0])

# Run reflection test
reflection_results = runner.run_reflection_test(TEST_CASES[2])
```

### 2. Run Individual Evaluators

#### Outcome-Based Evaluation
```python
from test_parse_user_input_eval import OutcomeEvaluator

evaluator = OutcomeEvaluator()

# Your parsed output
parsed_output = {
    "resource_type": "storage_account",
    "name": "mystorageacct",
    "region": "West Europe",
    "resource_group": "rg-deployment-test"
}

# Expected output
expected = {
    "resource_type": "storage_account",
    "name": "mystorageacct",
    "region": "West Europe",
    "resource_group": "rg-deployment-test"
}

result = evaluator.evaluate(
    user_input="Create a storage account named mystorageacct in West Europe",
    parsed_output=parsed_output,
    expected=expected
)

print(f"Score: {result['score']}")
print(f"Matches: {result['matches']}")
```

#### Rubric-Based Evaluation
```python
from test_parse_user_input_eval import RubricEvaluator, EVALUATION_RUBRIC, eval_llm

evaluator = RubricEvaluator(eval_llm, EVALUATION_RUBRIC)

result = evaluator.evaluate(
    user_input="Deploy a key vault named myvault in UK South with soft delete",
    parsed_output=parsed_output
)

print(f"Overall Score: {result['overall_score']:.2f}")
for dim, score in result['dimension_scores'].items():
    print(f"  {dim}: {score:.2f} - {result['feedback'][dim]}")
```

#### Reflection Pattern
```python
from test_parse_user_input_eval import ParseReflector, eval_llm

reflector = ParseReflector(eval_llm, score_threshold=0.85)

result = reflector.parse_with_reflection(
    user_input="Deploy a secure storage account named securedata in West US with HTTPS only",
    max_iterations=3
)

print(f"Final Score: {result['final_score']:.2f}")
print(f"Iterations: {result['iterations']}")
print(f"Final Output: {result['final_output']}")
```

## Test Dataset

The suite includes 7 comprehensive test cases covering:

- ✅ Basic resource creation (minimal fields)
- ✅ Resources with SKU/performance tiers
- ✅ Resources with security configurations
- ✅ Resources with custom tags
- ✅ Explicit vs. default resource groups
- ✅ Different Azure resource types (storage, key vault, app service)
- ✅ Complex multi-field configurations

## Evaluation Rubric

The rubric evaluates 5 dimensions:

| Dimension | Weight | Description |
|-----------|--------|-------------|
| required_fields | 35% | All required fields present and correct |
| optional_fields | 25% | Optional fields from input correctly parsed |
| defaults | 15% | Default values set when not specified |
| data_accuracy | 15% | Valid Azure values (regions, SKUs, etc.) |
| json_validity | 10% | Output is valid, parseable JSON |

## Adding New Test Cases

```python
from test_parse_user_input_eval import TEST_CASES

# Add to TEST_CASES list
new_test = {
    "test_id": "my_custom_test",
    "user_input": "Create a storage account...",
    "expected": {
        "resource_type": "storage_account",
        "name": "myname",
        "region": "East US",
        # ... other expected fields
    },
    "description": "Description of what this tests"
}

TEST_CASES.append(new_test)
```

## Understanding Results

### Outcome-Based Results
```python
{
    "matches": True,  # True if output exactly matches expected
    "missing_fields": [],  # Fields expected but not present
    "incorrect_fields": {},  # Fields with wrong values
    "score": 1.0  # 0-1 score based on correctness
}
```

### Rubric-Based Results
```python
{
    "dimension_scores": {  # Each dimension scored 0-1
        "required_fields": 0.8,
        "optional_fields": 1.0,
        # ...
    },
    "overall_score": 0.87,  # Weighted average
    "feedback": {  # LLM feedback per dimension
        "required_fields": "All fields present but region name slightly non-standard",
        # ...
    }
}
```

### Reflection Results
```python
{
    "final_output": {...},  # Best output after iterations
    "iterations": 2,  # Number of iterations run
    "evaluation_history": [...],  # Score progression
    "final_score": 0.92  # Final score achieved
}
```

## Best Practices

### 1. Setting Thresholds
- For critical deployments: `score_threshold=0.90` or higher
- For development/testing: `score_threshold=0.75-0.85`
- Adjust based on your quality requirements

### 2. Iteration Limits
- Default: `max_iterations=3` (good balance)
- Complex cases: Increase to 5
- Simple cases: Can reduce to 2

### 3. Choosing Evaluation Method

| Use Case | Recommended Method |
|----------|-------------------|
| Regression testing | Outcome-Based |
| Quality improvement | Rubric-Based |
| Production optimization | Reflection Pattern |
| CI/CD pipeline | Outcome-Based (fast) |
| Manual review | Rubric-Based (detailed) |

### 4. Convergence Detection
If using reflection, monitor the evaluation_history:
```python
scores = [e['evaluation']['overall_score'] for e in result['evaluation_history']]
improvement = scores[-1] - scores[0]

if improvement < 0.05:
    print("⚠️ Limited improvement - may need better prompts")
```

## Integration with CI/CD

```python
# Example: Fail build if pass rate < 80%
results = runner.run_outcome_based_tests()

if results['summary']['pass_rate'] < 0.8:
    print(f"❌ Tests failed: {results['summary']['pass_rate']:.1%} pass rate")
    exit(1)
else:
    print(f"✅ Tests passed: {results['summary']['pass_rate']:.1%} pass rate")
```

## Troubleshooting

### Low Scores on required_fields
- Check that the parse prompt clearly specifies required fields
- Verify LLM is extracting resource_type, region, name

### Low Scores on defaults
- Ensure prompt explicitly states default values to use
- Check logic for setting defaults when fields are missing

### Low Scores on data_accuracy
- Validate Azure region names against official list
- Check SKU/tier combinations are valid for resource type

### Reflection Not Improving
- Increase LLM temperature slightly for more variation
- Make feedback more specific and actionable
- Consider using a more capable model for refinement

## Example: Full Workflow

```python
# 1. Quick check with outcome-based
outcome = runner.run_outcome_based_tests()
print(f"Pass rate: {outcome['summary']['pass_rate']:.1%}")

# 2. Deep dive on failures
for result in outcome['results']:
    if not result['passed']:
        print(f"\n❌ Failed: {result['test_id']}")
        
        # Run rubric eval for details
        test_case = next(t for t in TEST_CASES if t['test_id'] == result['test_id'])
        rubric = runner.run_rubric_evaluation(test_case)
        
        # If score is really low, try reflection
        if rubric['overall_score'] < 0.7:
            reflection = runner.run_reflection_test(test_case)
            print(f"After reflection: {reflection['final_score']:.2f}")
```

## Next Steps

1. Run the full test suite: `python test_parse_user_input_eval.py`
2. Review failed tests and identify patterns
3. Use rubric evaluation to understand specific weaknesses
4. Apply reflection pattern to improve prompts
5. Add more test cases for edge cases
6. Integrate into CI/CD pipeline

---

For more details on evaluation patterns, see the [agentic-eval skill](.github/skills/SKILL.md).
