# ============================================================================
# services/device_import_service.py
# ============================================================================

import csv
import io
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from db_models import DeviceDB
from models.enums import VendorType, DeviceStatus
from shared.logger import setup_logger

logger = setup_logger(__name__)


class DeviceImportService:
    """Service for bulk importing devices from CSV/Excel"""

    # Only include fields that actually exist on DeviceDB
    REQUIRED_FIELDS = ["hostname", "ip", "vendor"]
    OPTIONAL_FIELDS = ["port", "username", "password"]
    ALL_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS

    @staticmethod
    def parse_csv(csv_content: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Parse CSV content and return list of device dictionaries

        Returns:
            Tuple of (devices, errors)
        """
        devices = []
        errors = []

        try:
            # Parse CSV
            csv_file = io.StringIO(csv_content)
            reader = csv.DictReader(csv_file)

            # Validate headers
            if not reader.fieldnames:
                errors.append("CSV file has no headers")
                return devices, errors

            headers = [h.strip().lower() for h in reader.fieldnames]

            # Check for required fields
            missing_fields = [f for f in DeviceImportService.REQUIRED_FIELDS if f not in headers]
            if missing_fields:
                errors.append(f"Missing required fields: {', '.join(missing_fields)}")
                return devices, errors

            # Process rows
            row_number = 1
            for row in reader:
                row_number += 1

                # Normalize keys
                normalized_row = {k.strip().lower(): v.strip() if v else None for k, v in row.items()}

                # Validate required fields
                missing = [f for f in DeviceImportService.REQUIRED_FIELDS if not normalized_row.get(f)]
                if missing:
                    errors.append(f"Row {row_number}: Missing required fields: {', '.join(missing)}")
                    continue

                # Validate vendor
                vendor_str = normalized_row["vendor"].upper().replace("-", "_")
                try:
                    vendor = VendorType[vendor_str]
                except KeyError:
                    errors.append(f"Row {row_number}: Invalid vendor '{normalized_row['vendor']}'. Must be one of: {', '.join([v.value for v in VendorType])}")
                    continue

                # Parse port
                port = normalized_row.get("port", "830")
                try:
                    port = int(port) if port else 830
                except ValueError:
                    errors.append(f"Row {row_number}: Invalid port '{port}', using default 830")
                    port = 830

                # Build device dictionary - only include fields that exist on DeviceDB
                device = {
                    "hostname": normalized_row["hostname"],
                    "ip": normalized_row["ip"],
                    "vendor": vendor.value,
                    "port": port,
                    "username": normalized_row.get("username"),
                    "password": normalized_row.get("password"),
                    "status": DeviceStatus.DISCOVERED.value,
                    "compliance": 0.0
                }

                devices.append(device)

        except Exception as e:
            logger.error(f"Failed to parse CSV: {str(e)}")
            errors.append(f"CSV parsing error: {str(e)}")

        return devices, errors

    @staticmethod
    def import_devices(
        db: Session,
        devices: List[Dict[str, Any]],
        update_existing: bool = False
    ) -> Tuple[int, int, List[str]]:
        """
        Import devices into database

        Args:
            db: Database session
            devices: List of device dictionaries
            update_existing: If True, update existing devices instead of skipping

        Returns:
            Tuple of (created_count, updated_count, errors)
        """
        created_count = 0
        updated_count = 0
        errors = []

        for device_data in devices:
            try:
                hostname = device_data["hostname"]

                # Check if device already exists
                existing_device = db.query(DeviceDB).filter(
                    DeviceDB.hostname == hostname
                ).first()

                if existing_device:
                    if update_existing:
                        # Update existing device
                        for key, value in device_data.items():
                            if value is not None and hasattr(existing_device, key):
                                setattr(existing_device, key, value)
                        updated_count += 1
                        logger.info(f"Updated existing device: {hostname}")
                    else:
                        errors.append(f"Device '{hostname}' already exists (skipped)")
                        continue
                else:
                    # Create new device
                    db_device = DeviceDB(**device_data)
                    db.add(db_device)
                    created_count += 1
                    logger.info(f"Created new device: {hostname}")

            except Exception as e:
                logger.error(f"Failed to import device '{device_data.get('hostname', 'unknown')}': {str(e)}")
                errors.append(f"Failed to import '{device_data.get('hostname', 'unknown')}': {str(e)}")

        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Database commit failed: {str(e)}")
            errors.append(f"Database commit failed: {str(e)}")
            return 0, 0, errors

        return created_count, updated_count, errors

    @staticmethod
    def generate_csv_template() -> str:
        """Generate a CSV template for device import"""
        template_rows = [
            DeviceImportService.ALL_FIELDS,
            [
                "router1",              # hostname
                "192.168.1.1",         # ip
                "CISCO_XR",            # vendor
                "830",                  # port
                "admin",                # username
                "password123"           # password
            ],
            [
                "switch1",              # hostname
                "192.168.1.2",         # ip
                "NOKIA_SROS",          # vendor
                "830",                  # port
                "admin",                # username
                "password456"           # password
            ]
        ]

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerows(template_rows)

        return output.getvalue()

    @staticmethod
    def export_devices_to_csv(db: Session) -> str:
        """Export all devices to CSV format"""
        devices = db.query(DeviceDB).all()

        # Export fields that actually exist on DeviceDB
        export_fields = ["hostname", "ip", "vendor", "port", "username", "password"]

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=export_fields)
        writer.writeheader()

        for device in devices:
            writer.writerow({
                "hostname": device.hostname,
                "ip": device.ip or "",
                "vendor": device.vendor.value if hasattr(device.vendor, 'value') else str(device.vendor),
                "port": device.port,
                "username": device.username or "",
                "password": "***REDACTED***",  # Don't export passwords
            })

        return output.getvalue()
