#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Input validation utilities for the Electrode Profile Generator.

Author: Pau Bas Calopa
Version: 1.3.0
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
    Input validation for the Electrode Profile Generator.

    Provides numerical and string validation with optional range constraints.
    Handles European decimal format (comma → dot) automatically.

    Usage Examples:
        validator = InputValidator()

        result = validator.validate_float("12,5")
        if result.is_valid:
            value = result.value  # 12.5

        result = validator.validate_integer("100", max_value=500)
    """

    def __init__(self):
        """Initialize InputValidator."""
        pass

    # =================================================================
    # MAIN VALIDATION METHODS
    # =================================================================

    def validate_float(self,
                      value: str,
                      min_value: Optional[float] = None,
                      max_value: Optional[float] = None,
                      allow_negative: bool = True) -> ValidationResult:
        """
        Validate floating-point numerical input.

        No hardcoded limits unless explicitly provided by caller.

        Args:
            value: Input string to validate
            min_value: Minimum allowed value (None = no minimum limit)
            max_value: Maximum allowed value (None = no maximum limit)
            allow_negative: Whether negative numbers are allowed

        Returns:
            ValidationResult with validated float value or error message
        """
        try:
            original_value = str(value).strip() if value is not None else ""

            if not original_value:
                return ValidationResult(False, None, "Input cannot be empty", original_value)

            if any(c.isalpha() for c in original_value):
                return ValidationResult(False, None, "Letters not allowed - numbers only", original_value)

            cleaned_value = self._clean_numerical_input_strict(original_value)

            if not cleaned_value:
                return ValidationResult(False, None, "Invalid number format", original_value)

            try:
                float_value = float(cleaned_value)
            except ValueError:
                return ValidationResult(False, None, "Invalid number format", original_value)

            if not allow_negative and float_value < 0:
                return ValidationResult(False, None, "Negative numbers not allowed", original_value)

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
        Validate integer numerical input.

        Args:
            value: Input string to validate
            min_value: Minimum allowed value (None = no minimum limit)
            max_value: Maximum allowed value (None = no maximum limit)
            allow_negative: Whether negative numbers are allowed

        Returns:
            ValidationResult with validated integer value or error message
        """
        try:
            float_result = self.validate_float(value, min_value, max_value, allow_negative)

            if not float_result.is_valid:
                return ValidationResult(False, None, float_result.error_message, float_result.original_value)

            int_value = round(float_result.value)

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
        Validate string input.

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
            cleaned_value = original_value.strip()

            if not cleaned_value and not allow_empty:
                return ValidationResult(False, None, "Input cannot be empty", original_value)

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
        Clean numerical input — handle decimal point correction only.

        - "12,5" → "12.5" (European decimal comma)
        - "1.234,56" → "1234.56" (European thousands separator)
        - "8.8.0" → "" (invalid — multiple decimal points)
        """
        try:
            if not value:
                return ""

            cleaned = value.replace(' ', '')

            if ',' in cleaned and '.' in cleaned:
                last_comma = cleaned.rfind(',')
                last_dot = cleaned.rfind('.')

                if last_comma > last_dot:
                    cleaned = cleaned.replace('.', '').replace(',', '.')
                else:
                    cleaned = cleaned.replace(',', '')
            elif ',' in cleaned:
                cleaned = cleaned.replace(',', '.')

            if cleaned.count('.') > 1:
                return ""

            number_pattern = r'^[-]?\d*\.?\d*$'

            if re.match(number_pattern, cleaned) and len(cleaned.replace('-', '').replace('.', '')) > 0:
                if cleaned.startswith('.'):
                    cleaned = '0' + cleaned
                elif cleaned.startswith('-.'):
                    cleaned = '-0' + cleaned[1:]

                if cleaned in ['.', '-', '-.'] or cleaned.replace('-', '').replace('.', '') == '':
                    return ""

                return cleaned

            return ""

        except Exception as e:
            SystemLogger.error(f"_clean_numerical_input_strict error: {e}", exc_info=True)
            return ""
