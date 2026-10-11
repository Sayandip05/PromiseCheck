"""Customers domain module public interface."""

from modules.customers.models import Customer
from modules.customers.service import CustomerService

__all__ = [
    "Customer",
    "CustomerService",
]
