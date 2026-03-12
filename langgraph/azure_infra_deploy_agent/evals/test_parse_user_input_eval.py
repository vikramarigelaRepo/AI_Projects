"""
Evaluations for parse_user_input LLM output using agentic-eval patterns.

This module implements multiple evaluation strategies:
- Rubric-based evaluation for comprehensive scoring
- Outcome-based evaluation for correctness
- Reflection pattern for iterative improvement
"""

import json
from typing import TypedDict, Literal, Any
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize LLM for evaluations

eval_llm = ChatOpenAI(
    model="gpt-5-mini",  # Fixed model name
    base_url=os.getenv("AZURE_OPENAI_ENDPOINT"),  # Use environment variable for base URL
    api_key=os.getenv("AZURE_OPENAI_KEY")  # Use environment variable for API key
)


# ============================================================================
# Test Dataset - Diverse real-world scenarios
# ============================================================================

TEST_CASES = [
    {
        "test_id": "basic_storage_account",
        "user_input": "Create a storage account named mystorageacct in West Europe",
        "expected": {
            "resource_type": "storage_account",
            "name": "mystorageacct",
            "region": "West Europe",
            "resource_group": "rg-deployment-test"  # default
        },
        "description": "Basic storage account request with minimal fields"
    },
    {
        "test_id": "storage_with_sku",
        "user_input": "I need a premium storage account called premiumstore in East US with zone redundancy",
        "expected": {
            "resource_type": "storage_account",
            "name": "premiumstore",
            "region": "East US",
            "performance": "Premium",
            "zone_redundancy_enabled": True
        },
        "description": "Storage account with performance tier and zone redundancy"
    },
    {
        "test_id": "key_vault_full",
        "user_input": "Deploy a key vault named myvault in UK South with soft delete enabled for 30 days and purge protection",
        "expected": {
            "resource_type": "key_vault",
            "name": "myvault",
            "region": "UK South",
            "soft_delete_enabled": True,
            "soft_delete_retention_days": 30,
            "purge_protection_enabled": True
        },
        "description": "Key vault with multiple specific configurations"
    },
    {
        "test_id": "app_service_linux",
        "user_input": "Create a Linux app service plan named webapp-plan in Central US with Basic B1 tier",
        "expected": {
            "resource_type": "app_service_plan",
            "name": "webapp-plan",
            "region": "Central US",
            "tier": "Basic",
            "sku": "B1",
            "reserved": True  # Linux
        },
        "description": "App service plan with OS and tier specification"
    },
    {
        "test_id": "storage_with_tags",
        "user_input": "Deploy storage account datastore123 in North Europe with tags environment=production and owner=devops",
        "expected": {
            "resource_type": "storage_account",
            "name": "datastore123",
            "region": "North Europe",
            "tags": {
                "environment": "production",
                "owner": "devops"
            }
        },
        "description": "Resource with custom tags"
    },
    {
        "test_id": "explicit_resource_group",
        "user_input": "Create storage account myapp-storage in East US 2 within resource group rg-production",
        "expected": {
            "resource_type": "storage_account",
            "name": "myapp-storage",
            "region": "East US 2",
            "resource_group": "rg-production"
        },
        "description": "Explicit resource group instead of default"
    },
    {
        "test_id": "storage_security_settings",
        "user_input": "Deploy a secure storage account named securedata in West US with HTTPS only, TLS 1.2, and no public blob access",
        "expected": {
            "resource_type": "storage_account",
            "name": "securedata",
            "region": "West US",
            "enable_https_traffic_only": True,
            "min_tls_version": "TLS1_2",
            "allow_blob_public_access": False
        },
        "description": "Security-focused storage configuration"
    },
]


# ============================================================================
# Evaluation Rubric
# ============================================================================

EVALUATION_RUBRIC = {
    "required_fields": {
        "weight": 0.35,
        "description": "All required fields (resource_type, region, name) are present and correct"
    },
    "optional_fields": {
        "weight": 0.25,
        "description": "Optional fields mentioned in input are correctly parsed"
    },
    "defaults": {
        "weight": 0.15,
        "description": "Default values (like resource_group) are set when not specified"
    },
    "data_accuracy": {
        "weight": 0.15,
        "description": "Field values are accurate and valid for Azure (correct regions, SKUs, etc.)"
    },
    "json_validity": {
        "weight": 0.10,
        "description": "Output is valid, parseable JSON"
    }
}


# ============================================================================
# Pattern 1: Outcome-Based Evaluation
# ============================================================================

class OutcomeEvaluator:
    """Evaluates whether parsed output matches expected structure."""
    
    def evaluate(self, user_input: str, parsed_output: dict, expected: dict) -> dict:
        """
        Compare parsed output against expected outcome.
        
        Returns:
            {
                "matches": bool,
                "missing_fields": list,
                "incorrect_fields": dict,
                "extra_fields": list,
                "score": float (0-1)
            }
        """
        result = {
            "matches": True,
            "missing_fields": [],
            "incorrect_fields": {},
            "extra_fields": [],
            "score": 1.0
        }
        
        # Check for missing required fields
        for key, value in expected.items():
            if key not in parsed_output:
                result["missing_fields"].append(key)
                result["matches"] = False
            elif parsed_output[key] != value:
                # For nested dicts (like tags), do deep comparison
                if isinstance(value, dict) and isinstance(parsed_output[key], dict):
                    if parsed_output[key] != value:
                        result["incorrect_fields"][key] = {
                            "expected": value,
                            "actual": parsed_output[key]
                        }
                        result["matches"] = False
                else:
                    result["incorrect_fields"][key] = {
                        "expected": value,
                        "actual": parsed_output[key]
                    }
                    result["matches"] = False
        
        # Calculate score
        total_expected = len(expected)
        errors = len(result["missing_fields"]) + len(result["incorrect_fields"])
        result["score"] = max(0, 1 - (errors / total_expected)) if total_expected > 0 else 1.0
        
        return result


# ============================================================================
# Pattern 2: Rubric-Based Evaluation with LLM-as-Judge
# ============================================================================

class RubricEvaluator:
    """Evaluates parsed output using weighted rubric with LLM scoring."""
    
    def __init__(self, llm, rubric: dict):
        self.llm = llm
        self.rubric = rubric
    
    def evaluate(self, user_input: str, parsed_output: dict) -> dict:
        """
        Evaluate output against rubric dimensions.
        
        Returns:
            {
                "dimension_scores": dict,
                "overall_score": float (0-1),
                "feedback": dict
            }
        """
        prompt = f"""
You are evaluating the quality of an LLM parse operation. The LLM parsed a user's natural language request into structured JSON for Azure resource deployment.

User Input: {user_input}

Parsed Output: {json.dumps(parsed_output, indent=2)}

Evaluate the parsed output on these dimensions (rate each 1-5):

1. required_fields (1-5): Are resource_type, region, and name present and correct?
2. optional_fields (1-5): Are optional fields mentioned in the input correctly extracted?
3. defaults (1-5): Are default values (like resource_group="rg-deployment-test") properly set when not specified?
4. data_accuracy (1-5): Are values valid for Azure (correct region names, valid SKUs, proper data types)?
5. json_validity (1-5): Is the output valid JSON with proper structure?

For each dimension, also provide brief feedback explaining the score.

Return ONLY valid JSON in this format:
{{
    "required_fields": {{"score": <1-5>, "feedback": "<explanation>"}},
    "optional_fields": {{"score": <1-5>, "feedback": "<explanation>"}},
    "defaults": {{"score": <1-5>, "feedback": "<explanation>"}},
    "data_accuracy": {{"score": <1-5>, "feedback": "<explanation>"}},
    "json_validity": {{"score": <1-5>, "feedback": "<explanation>"}}
}}
"""
        
        response = self.llm.invoke(prompt)
        content = response.content.strip()
        
        # Extract JSON from response (handle markdown blocks)
        if content.startswith('```'):
            lines = content.split('\n')
            lines = [l for l in lines if not l.strip().startswith('```')]
            content = '\n'.join(lines)
        
        dimension_results = json.loads(content)
        
        # Calculate weighted overall score
        overall_score = 0.0
        dimension_scores = {}
        feedback = {}
        
        for dimension, config in self.rubric.items():
            if dimension in dimension_results:
                score_1_5 = dimension_results[dimension]["score"]
                normalized = score_1_5 / 5.0  # Normalize to 0-1
                dimension_scores[dimension] = normalized
                feedback[dimension] = dimension_results[dimension]["feedback"]
                overall_score += normalized * config["weight"]
        
        return {
            "dimension_scores": dimension_scores,
            "overall_score": overall_score,
            "feedback": feedback
        }


# ============================================================================
# Pattern 3: Reflection and Improvement
# ============================================================================

class ParseReflector:
    """Implements reflection pattern to improve parse quality through self-critique."""
    
    def __init__(self, llm, score_threshold: float = 0.85):
        self.llm = llm
        self.score_threshold = score_threshold
        self.evaluator = RubricEvaluator(llm, EVALUATION_RUBRIC)
    
    def parse_with_reflection(
        self, 
        user_input: str, 
        max_iterations: int = 3
    ) -> dict:
        """
        Parse user input with iterative reflection and improvement.
        
        Returns:
            {
                "final_output": dict,
                "iterations": int,
                "evaluation_history": list,
                "final_score": float
            }
        """
        iterations_history = []
        
        # Initial parse
        parsed_output = self._parse_user_input(user_input)
        
        for i in range(max_iterations):
            # Evaluate current output
            evaluation = self.evaluator.evaluate(user_input, parsed_output)
            
            iterations_history.append({
                "iteration": i + 1,
                "output": parsed_output.copy(),
                "evaluation": evaluation
            })
            
            print(f"Iteration {i+1}: Score = {evaluation['overall_score']:.2f}")
            
            # Check if good enough
            if evaluation["overall_score"] >= self.score_threshold:
                print(f"✅ Reached threshold ({self.score_threshold}) in {i+1} iterations")
                break
            
            # If not last iteration, refine
            if i < max_iterations - 1:
                parsed_output = self._refine_parse(
                    user_input, 
                    parsed_output, 
                    evaluation
                )
        
        return {
            "final_output": parsed_output,
            "iterations": len(iterations_history),
            "evaluation_history": iterations_history,
            "final_score": iterations_history[-1]["evaluation"]["overall_score"]
        }
    
    def _parse_user_input(self, user_input: str) -> dict:
        """Initial parse operation."""
        prompt = f"""
You are an expert in parsing user requests into structured JSON format for Azure resource deployments.
Convert the following user request into a structured JSON format:

User Request: {user_input}

Return a JSON with these fields (include only fields mentioned or implied in the request):

REQUIRED FIELDS:
- resource_type: the type of Azure resource (e.g., "storage_account", "key_vault", "app_service_plan")
- region: the Azure region (e.g., "East US", "West Europe")
- name: the name for the resource
- resource_group: the resource group name (if not specified, use "rg-deployment-test" as default)

OPTIONAL FIELDS:
- sku, tier, kind, api_version, capacity, zone_redundancy_enabled
- Storage: performance, replication_type, access_tier, enable_https_traffic_only, min_tls_version, allow_blob_public_access
- Key Vault: soft_delete_enabled, soft_delete_retention_days, purge_protection_enabled, enable_rbac_authorization
- App Service: reserved (true for Linux), per_site_scaling
- Networking: public_network_access
- tags: object with key-value pairs

Return ONLY valid JSON without any markdown formatting or explanations.
"""
        
        response = self.llm.invoke(prompt)
        content = response.content.strip()
        
        # Clean and parse JSON
        if content.startswith('```'):
            lines = content.split('\n')
            lines = [l for l in lines if not l.strip().startswith('```')]
            content = '\n'.join(lines)
        
        return json.loads(content)
    
    def _refine_parse(
        self, 
        user_input: str, 
        current_output: dict, 
        evaluation: dict
    ) -> dict:
        """Refine parse based on evaluation feedback."""
        prompt = f"""
You previously parsed this user request:
User Request: {user_input}

Your Output: {json.dumps(current_output, indent=2)}

However, the evaluation found issues:
{json.dumps(evaluation['feedback'], indent=2)}

Overall Score: {evaluation['overall_score']:.2f}

Please improve the parsed output to address the feedback. Pay special attention to:
- Ensuring all required fields are present and accurate
- Correctly extracting optional fields mentioned in the request
- Setting proper defaults (resource_group="rg-deployment-test" if not specified)
- Using valid Azure values (correct region names, proper SKUs, etc.)

Return ONLY the improved JSON without markdown or explanations.
"""
        
        response = self.llm.invoke(prompt)
        content = response.content.strip()
        
        # Clean and parse JSON
        if content.startswith('```'):
            lines = content.split('\n')
            lines = [l for l in lines if not l.strip().startswith('```')]
            content = '\n'.join(lines)
        
        return json.loads(content)


# ============================================================================
# Test Runner
# ============================================================================

class ParseEvaluationRunner:
    """Runs comprehensive evaluations on parse_user_input."""
    
    def __init__(self, llm):
        self.llm = llm
        self.outcome_evaluator = OutcomeEvaluator()
        self.rubric_evaluator = RubricEvaluator(llm, EVALUATION_RUBRIC)
        self.reflector = ParseReflector(llm)
    
    def run_outcome_based_tests(self, test_cases: list = None) -> dict:
        """Run outcome-based evaluation on test cases."""
        test_cases = test_cases or TEST_CASES
        
        print("\n" + "="*70)
        print("OUTCOME-BASED EVALUATION")
        print("="*70)
        
        results = []
        
        for test_case in test_cases:
            print(f"\n📋 Test: {test_case['test_id']}")
            print(f"   {test_case['description']}")
            print(f"   Input: {test_case['user_input']}")
            
            # Simulate parse (in real scenario, call actual parse_user_input)
            parsed = self.reflector._parse_user_input(test_case['user_input'])
            
            # Evaluate
            evaluation = self.outcome_evaluator.evaluate(
                test_case['user_input'],
                parsed,
                test_case['expected']
            )
            
            print(f"   Score: {evaluation['score']:.2f}")
            
            if evaluation['matches']:
                print("   ✅ PASS")
            else:
                print("   ❌ FAIL")
                if evaluation['missing_fields']:
                    print(f"      Missing: {evaluation['missing_fields']}")
                if evaluation['incorrect_fields']:
                    print(f"      Incorrect: {list(evaluation['incorrect_fields'].keys())}")
            
            results.append({
                "test_id": test_case['test_id'],
                "passed": evaluation['matches'],
                "score": evaluation['score'],
                "evaluation": evaluation,
                "parsed_output": parsed
            })
        
        # Summary
        total = len(results)
        passed = sum(1 for r in results if r['passed'])
        avg_score = sum(r['score'] for r in results) / total if total > 0 else 0
        
        print(f"\n{'='*70}")
        print(f"SUMMARY: {passed}/{total} tests passed | Average Score: {avg_score:.2f}")
        print(f"{'='*70}\n")
        
        return {
            "results": results,
            "summary": {
                "total": total,
                "passed": passed,
                "pass_rate": passed / total if total > 0 else 0,
                "average_score": avg_score
            }
        }
    
    def run_rubric_evaluation(self, test_case: dict) -> dict:
        """Run rubric-based evaluation on a single test case."""
        print("\n" + "="*70)
        print("RUBRIC-BASED EVALUATION")
        print("="*70)
        
        print(f"\n📋 Test: {test_case['test_id']}")
        print(f"   {test_case['description']}")
        print(f"   Input: {test_case['user_input']}")
        
        # Parse
        parsed = self.reflector._parse_user_input(test_case['user_input'])
        print(f"\n   Parsed Output:\n{json.dumps(parsed, indent=6)}")
        
        # Evaluate with rubric
        evaluation = self.rubric_evaluator.evaluate(test_case['user_input'], parsed)
        
        print(f"\n   Overall Score: {evaluation['overall_score']:.2f}")
        print("\n   Dimension Breakdown:")
        
        for dimension, score in evaluation['dimension_scores'].items():
            weight = EVALUATION_RUBRIC[dimension]['weight']
            feedback = evaluation['feedback'][dimension]
            print(f"      {dimension}: {score:.2f} (weight: {weight:.2f})")
            print(f"         → {feedback}")
        
        return evaluation
    
    def run_reflection_test(self, test_case: dict) -> dict:
        """Run reflection pattern on a single test case."""
        print("\n" + "="*70)
        print("REFLECTION & IMPROVEMENT EVALUATION")
        print("="*70)
        
        print(f"\n📋 Test: {test_case['test_id']}")
        print(f"   {test_case['description']}")
        print(f"   Input: {test_case['user_input']}\n")
        
        # Run reflection
        result = self.reflector.parse_with_reflection(test_case['user_input'])
        
        print(f"\n   Final Output:\n{json.dumps(result['final_output'], indent=6)}")
        print(f"\n   Iterations: {result['iterations']}")
        print(f"   Final Score: {result['final_score']:.2f}")
        
        # Show improvement over iterations
        print("\n   Iteration Progress:")
        for iteration in result['evaluation_history']:
            print(f"      Iteration {iteration['iteration']}: {iteration['evaluation']['overall_score']:.2f}")
        
        return result


# ============================================================================
# Main Execution
# ============================================================================

if __name__ == "__main__":
    runner = ParseEvaluationRunner(eval_llm)
    
    print("\n🚀 Starting parse_user_input Evaluations\n")
    
    # 1. Run outcome-based tests on all cases
    outcome_results = runner.run_outcome_based_tests()
    
    # 2. Run detailed rubric evaluation on one complex case
    complex_case = TEST_CASES[6]  # Security settings case
    rubric_results = runner.run_rubric_evaluation(complex_case)
    
    # 3. Run reflection test on a challenging case
    reflection_results = runner.run_reflection_test(TEST_CASES[2])  # Key vault case
    
    print("\n" + "="*70)
    print("✅ All evaluations complete!")
    print("="*70)
