#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Pau Bas Calopa
Version: 1.3.0
Date: March 2026
License: MIT
"""

import re
import logging
from typing import Optional

SystemLogger = logging.getLogger("InputValidator")
SystemLogger.setLevel(logging.ERROR)
if not SystemLogger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('[%(asctime)s][%(levelname)s][InputValidator] %(message)s')
    handler.setFormatter(formatter)
    SystemLogger.addHandler(handler)


class ValidationResult:
    """
    Container for validation results.
    
    Attributes:
        is_valid (bool): Whether the validation passed
        value (any): The validated and corrected value
        error_message (str): Human-readable error message if validation failed
        original_value (str): The original input value for reference
    """
    
    def __init__(self, is_valid: bool, value: any = None, error_message: str = "", original_value: str = ""):
        self.is_valid = is_valid
        self.value = value
        self.error_message = error_message
        self.original_value = original_value
    
    def __bool__(self):
        """Allow ValidationResult to be used in boolean context."""
        return self.is_valid
    
    def __str__(self):
        if self.is_valid:
            return f"Valid: {self.value}"
        else:
            return f"Invalid: {self.error_message}"


class InputValidator:
    """
    Input validation class for AC Ramp Breakdown Test System.
    
    Focused on the actual validation needs of the project:
    - Decimal point correction (comma to dot)
    - Voltage/Current/Frequency validation
    - String validation for filenames and text inputs
    - Integer validation for ranges and counts
    
    Usage Examples:
        validator = InputValidator()
        
        # Validate voltage input with user-defined limits
        result = validator.validate_float("12,5", min_value=0, max_value=user_limit)
        if result.is_valid:
            voltage = result.value  # 12.5
        
        # Validate filename
        result = validator.validate_string("test file.csv", max_length=50)
        if result.is_valid:
            filename = result.value  # "test file.csv"
    """
    
    def __init__(self):
        """Initialize InputValidator with simplified settings."""
        pass  # No longer need unwanted_chars list since we reject letters

    # =================================================================
    # MAIN VALIDATION METHODS FOR THE PROJECT
    # =================================================================
    
    def validate_float(self, 
                      value: str, 
                      min_value: Optional[float] = None, 
                      max_value: Optional[float] = None,
                      allow_negative: bool = True) -> ValidationResult:
        """
        Validate floating-point numerical input with NO hardcoded limits by default.
        
        Philosophy: No limits unless explicitly provided by caller.
        User controls all constraints - no hidden validation rules.
        
        Main use cases in project:
        - Basic validation: validate_float("12.5") - accepts any valid number
        - User-controlled limits: validate_float("12.5", max_value=user_range_limit)
        - Logical constraints only: validate_float("12.5", allow_negative=False)
        
        Args:
            value: Input string to validate
            min_value: Minimum allowed value (None = no minimum limit)
            max_value: Maximum allowed value (None = no maximum limit) 
            allow_negative: Whether negative numbers are allowed (logical constraint)
            
        Returns:
            ValidationResult with validated float value or error message
            
        Examples:
            validate_float("12.5")                    # ✅ Valid: 12.5 (no limits)
            validate_float("12,5")                    # ✅ Valid: 12.5 (European format)
            validate_float("-50")                     # ✅ Valid: -50.0 (negative allowed by default)
            validate_float("-50", allow_negative=False) # ❌ Error: negative not allowed
            validate_float("12.5V")                   # ❌ Error: letters not allowed
            validate_float("1000", max_value=user_limit) # Validation against USER-SET limit only
        """
        try:
            original_value = str(value).strip() if value is not None else ""
            
            # Handle empty input
            if not original_value:
                return ValidationResult(False, None, "Input cannot be empty", original_value)
            
            # SIMPLIFIED: Always reject letters - no cleaning mode
            if any(c.isalpha() for c in original_value):
                return ValidationResult(False, None, "Letters not allowed - numbers only", original_value)
            
            # Clean numerical input (decimal point correction only)
            cleaned_value = self._clean_numerical_input_strict(original_value)
            
            if not cleaned_value:
                return ValidationResult(False, None, "Invalid number format", original_value)
            
            # Convert to float
            try:
                float_value = float(cleaned_value)
            except ValueError:
                return ValidationResult(False, None, "Invalid number format", original_value)
            
            # Check negative numbers
            if not allow_negative and float_value < 0:
                return ValidationResult(False, None, "Negative numbers not allowed", original_value)
            
            # Check range constraints
            if min_value is not None and float_value < min_value:
                return ValidationResult(False, None, f"Value must be at least {min_value}", original_value)
            
            if max_value is not None and float_value > max_value:
                return ValidationResult(False, None, f"Value must not exceed {max_value}", original_value)
            
            return ValidationResult(True, float_value, "", original_value)
            
        except Exception as e:
            SystemLogger.error(f"validate_float error: {e}", exc_info=True)
            return ValidationResult(False, None, f"Validation error: {e}", str(value))
    
    def validate_integer(self, 
                        value: str, 
                        min_value: Optional[int] = None, 
                        max_value: Optional[int] = None,
                        allow_negative: bool = True) -> ValidationResult:
        """
        Validate integer numerical input with NO hardcoded limits by default.
        
        Philosophy: No limits unless explicitly provided by caller.
        All constraints come from user configuration or logical necessity.
        
        Main use cases in project:
        - Count values: validate_integer("5") - any valid integer
        - User-defined ranges: validate_integer("100", max_value=user_max_count)
        
        Args:
            value: Input string to validate
            min_value: Minimum allowed value (None = no minimum limit)
            max_value: Maximum allowed value (None = no maximum limit)
            allow_negative: Whether negative numbers are allowed (logical constraint)
            
        Returns:
            ValidationResult with validated integer value or error message
        """
        try:
            # First validate as float (letters will be rejected)
            float_result = self.validate_float(value, min_value, max_value, allow_negative)
            
            if not float_result.is_valid:
                return ValidationResult(False, None, float_result.error_message, float_result.original_value)
            
            # Round to nearest integer
            int_value = round(float_result.value)
            
            # Re-check range after rounding
            if min_value is not None and int_value < min_value:
                return ValidationResult(False, None, f"Value must be at least {min_value}", float_result.original_value)
            
            if max_value is not None and int_value > max_value:
                return ValidationResult(False, None, f"Value must not exceed {max_value}", float_result.original_value)
            
            return ValidationResult(True, int_value, "", float_result.original_value)
            
        except Exception as e:
            SystemLogger.error(f"validate_integer error: {e}", exc_info=True)
            return ValidationResult(False, None, f"Validation error: {e}", str(value))
    
    def validate_string(self, 
                       value: str, 
                       min_length: Optional[int] = None, 
                       max_length: Optional[int] = None,
                       allow_empty: bool = False) -> ValidationResult:
        """
        Validate string input with NO hardcoded limits by default.
        
        Philosophy: No artificial length restrictions unless specifically needed.
        Let users decide appropriate string lengths for their use case.
        
        Main use cases in project:
        - Filenames: validate_string("test.csv") - any reasonable filename
        - User descriptions: validate_string("Test Description") - no artificial limits
        - Optional constraints: validate_string("short", max_length=user_limit) when needed
        
        Args:
            value: Input string to validate
            min_length: Minimum allowed length (None = no minimum)
            max_length: Maximum allowed length (None = no maximum)
            allow_empty: Whether empty strings are allowed
            
        Returns:
            ValidationResult with cleaned string or error message
        """
        try:
            original_value = str(value) if value is not None else ""
            
            # Strip whitespace
            cleaned_value = original_value.strip()
            
            # Check empty input
            if not cleaned_value and not allow_empty:
                return ValidationResult(False, None, "Input cannot be empty", original_value)
            
            # Check length constraints
            if min_length is not None and len(cleaned_value) < min_length:
                return ValidationResult(False, None, f"Must be at least {min_length} characters", original_value)
            
            if max_length is not None and len(cleaned_value) > max_length:
                return ValidationResult(False, None, f"Must not exceed {max_length} characters", original_value)
            
            return ValidationResult(True, cleaned_value, "", original_value)
            
        except Exception as e:
            SystemLogger.error(f"validate_string error: {e}", exc_info=True)
            return ValidationResult(False, None, f"Validation error: {e}", str(value))

    # =================================================================
    # UTILITY METHODS
    # =================================================================
    
    def _clean_numerical_input_strict(self, value: str) -> str:
        """
        Clean numerical input with strict approach - only handle decimal points.
        
        Handles only essential formatting:
        - "12,5" -> "12.5" (European decimal comma)
        - "1.234,56" -> "1234.56" (European thousands separator)
        - "8.8.0" -> "" (invalid - multiple decimal points)
        - Removes only spaces (not letters - those cause validation errors)
        
        Args:
            value: Raw input string (already verified to contain no letters)
            
        Returns:
            Cleaned numerical string or empty string if invalid
        """
        try:
            if not value:
                return ""
            
            # Remove only spaces (letters already rejected)
            cleaned = value.replace(' ', '')
            
            # Check for multiple decimal points (invalid cases like "8.8.0", "1.2.3")
            dot_count = cleaned.count('.')
            comma_count = cleaned.count(',')
            
            # Handle decimal point correction (comma to dot)
            # European format: "1.234,56" -> "1234.56" 
            # Simple format: "12,5" -> "12.5"
            
            if ',' in cleaned and '.' in cleaned:
                # European format with thousands separator
                # Assume the last separator is decimal point
                last_comma = cleaned.rfind(',')
                last_dot = cleaned.rfind('.')
                
                if last_comma > last_dot:
                    # Comma is decimal point: "1.234,56"
                    cleaned = cleaned.replace('.', '').replace(',', '.')
                else:
                    # Dot is decimal point: "1,234.56"
                    cleaned = cleaned.replace(',', '')
            elif ',' in cleaned:
                # Only comma, assume it's decimal point
                cleaned = cleaned.replace(',', '.')
            
            # After cleaning, check for multiple decimal points
            if cleaned.count('.') > 1:
                # Invalid: multiple decimal points like "8.8.0" or "1.2.3"
                return ""
            
            # Validate that result contains only valid number characters
            # Pattern: optional minus, digits, optional decimal point, optional digits
            import re
            number_pattern = r'^[-]?\d*\.?\d*$'  # Made last \d* optional to handle cases like "5."
            
            if re.match(number_pattern, cleaned) and len(cleaned.replace('-', '').replace('.', '')) > 0:
                # Fix cases like ".5" -> "0.5"
                if cleaned.startswith('.'):
                    cleaned = '0' + cleaned
                elif cleaned.startswith('-.'):
                    cleaned = '-0' + cleaned[1:]
                    
                # Reject cases that are just "." or "-" or empty after digits
                if cleaned in ['.', '-', '-.'] or cleaned.replace('-', '').replace('.', '') == '':
                    return ""
                    
                return cleaned
            
            return ""
            
        except Exception as e:
            SystemLogger.error(f"_clean_numerical_input_strict error: {e}", exc_info=True)
            return ""


# =================================================================
# CONVENIENCE FUNCTIONS FOR QUICK USE
# =================================================================

# Global validator instance for direct access if needed
_validator = InputValidator()
