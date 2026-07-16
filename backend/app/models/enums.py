from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "ADMIN"
    GESTOR = "GESTOR"
    ATENDENTE = "ATENDENTE"
    VISTORIADOR = "VISTORIADOR"
    VIEWER = "VIEWER"


class TrailerStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    RENTED = "RENTED"
    MAINTENANCE = "MAINTENANCE"
    INACTIVE = "INACTIVE"


class RentalStatus(StrEnum):
    DRAFT = "DRAFT"
    RESERVED = "RESERVED"
    ACTIVE = "ACTIVE"
    OVERDUE = "OVERDUE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class PeriodType(StrEnum):
    DAYS = "DAYS"
    HOURS = "HOURS"


class InspectionType(StrEnum):
    PICKUP = "PICKUP"
    RETURN = "RETURN"


class MaintenancePriority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class MaintenanceStatus(StrEnum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ChargeType(StrEnum):
    RENTAL = "RENTAL"
    LATE = "LATE"
    DISCOUNT = "DISCOUNT"
    CLEANING = "CLEANING"
    DAMAGE = "DAMAGE"
    ADJUSTMENT = "ADJUSTMENT"


class PaymentMethod(StrEnum):
    CASH = "CASH"
    PIX = "PIX"
    CARD = "CARD"
    TRANSFER = "TRANSFER"
    OTHER = "OTHER"


class PaymentStatus(StrEnum):
    CONFIRMED = "CONFIRMED"
    REFUNDED = "REFUNDED"


class DocumentType(StrEnum):
    CONTRACT = "CONTRACT"
    PICKUP_TERM = "PICKUP_TERM"
    RETURN_TERM = "RETURN_TERM"
    RECEIPT = "RECEIPT"
    EXTRA_RECEIPT = "EXTRA_RECEIPT"
