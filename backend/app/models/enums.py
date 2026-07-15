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
