"""MediMate Internationalization (i18n) Engine.

Provides seamless, instantaneous English <-> Bangla translation with single-click
toggling, dynamic listener updates, parameter interpolation, and persistent state.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Active language state: "en" or "bn"
_current_language: str = "en"
_listeners: List[Callable[[str], None]] = []

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        # App / Navigation
        "app_title": "MediMate",
        "nav_medicines": "Medicines",
        "nav_schedule": "Schedule",
        "nav_history": "History",
        "nav_alerts": "Alerts",
        "nav_profile": "Profile",
        "logout": "Log out",
        "pairing_code": "Pairing Code",
        "connect": "Connect",
        "close": "Close",
        "cancel": "Cancel",
        "save": "Save",
        "delete": "Delete",
        "edit": "Edit",
        "back": "Back",
        "all": "All",
        "daily": "Daily",
        "everyday": "Every day",

        # Auth
        "sign_up": "Sign up",
        "log_in": "Log in",
        "sign_in_to_continue": "Sign in to continue.",
        "log_in_to_continue": "Log in to continue.",
        "already_have_account": "Already have an account? Log in",
        "signup_link": "Signup !",
        "name": "NAME",
        "role": "ROLE",
        "email": "E-MAIL",
        "password": "PASSWORD",
        "patient": "Patient",
        "caretaker": "Caretaker",
        "name_hint": "e.g. Oyshikee Sithee",
        "email_hint": "e.g. sithee123@gmail.com",
        "password_hint": "******",
        "all_fields_required": "All fields are required.",
        "email_password_required": "Email and password are required.",
        "welcome_user": "Welcome, {name}!",
        "welcome_back_user": "Welcome back, {name}!",

        # Header Greetings
        "good_morning": "Good Morning, {name}",
        "good_afternoon": "Good Afternoon, {name}",
        "good_evening": "Good Evening, {name}",
        "hello_caregiver": "Hello, Caregiver {name}",

        # Patient Dashboard
        "todays_medicines": "TODAY'S MEDICINES",
        "todays_progress": "TODAY'S PROGRESS",
        "doses_taken": "{taken} / {total} Doses Taken",
        "meds_remaining": "{count} medicine remaining",
        "meds_remaining_plural": "{count} medicines remaining",
        "all_doses_complete": "All doses complete for today! Great job!",
        "no_meds_scheduled": "No medicines scheduled for today",
        "take_now": "Take Now",
        "taken": "Taken",
        "snooze": "Snooze",
        "skip": "Skip",
        "missed": "Missed",
        "pending": "Pending",

        # Dose Tracking & Rescheduling
        "dose_tracking_reschedule": "DOSE TRACKING & RESCHEDULE",
        "dose_tracking_desc": "Track stock, consumption & projected reschedule dates",
        "view_tracking_reschedule": "View Dose Tracking & Reschedule",
        "tracking_subtitle": "Stock consumption & reschedule forecasts",
        "tab_schedules": "⏰ Dose Schedules",
        "tab_tracking": "🔄 Tracking & Reschedule",
        "no_tracking_items": "No medications tracked yet.",
        "stock": "Stock",
        "units": "units",
        "pills": "pills",
        "frequency": "Frequency",
        "days_supply_left": "days supply left",
        "reschedule_due": "Reschedule Due",
        "reschedule_now": "Reschedule Now",
        "reschedule_soon": "Reschedule Soon",
        "supply_healthy": "Supply Healthy",
        "healthy_stock": "Healthy Supply",
        "reschedule_btn": "Reschedule",
        "immediate": "Immediate",
        "confirm_reschedule": "CONFIRM RESCHEDULE",
        "reschedule_refill_title": "Reschedule & Refill: {name}",
        "current_stock_label": "Current Stock: {stock} units",
        "frequency_label": "Frequency: {freq}",
        "supply_remaining_label": "Supply Remaining: {days} days",
        "projected_reschedule_label": "Projected Reschedule: {date}",
        "added_stock_label": "Added Stock (Units / Pills)",
        "rescheduled_toast": "Rescheduled {name}! +{qty} added to stock.",
        "reschedule_failed": "Failed rescheduling: {err}",

        # Hamburger Dropdown Menu
        "menu_dashboard": "Dashboard",
        "menu_schedules": "Dose Schedules",
        "menu_tracking": "Dose Tracking & Reschedule",
        "menu_medicines": "All Medicines",
        "menu_insulin": "Insulin History",
        "menu_pairing": "Pairing Code",
        "menu_history": "Medication History",
        "menu_profile": "Profile",
        "menu_logout": "Log Out",

        # Profile Card
        "profile_patient_title": "Patient Profile",
        "profile_caregiver_title": "Caregiver Profile",
        "profile_health_vitals": "Health Vitals & Medical Info",
        "profile_blood_group": "Blood Group",
        "profile_age_gender": "Age & Gender",
        "profile_weight_height": "Weight & Height",
        "profile_emergency_phone": "Emergency Contact",
        "profile_allergies_conditions": "Allergies & Conditions",
        "profile_pairing_code": "Caregiver Pairing Code",
        "profile_linked_patient": "Active Patient",
        "profile_generate_code": "Generate Code",
        "profile_connect_patient": "Connect Patient",
        "profile_edit_btn": "Edit Health Info",
        "profile_edit_title": "Edit Health Information",
        "profile_save_btn": "Save Details",
        "profile_logout_btn": "Log Out",
        "profile_years_old": "Yrs",
        "profile_updated_toast": "Profile details updated successfully!",

        # History View
        "history_title": "History",
        "history_calendar_title": "History Calender",
        "no_doses_on_date": "No medications scheduled on this date.",
        "all_taken_legend": "All medications taken",
        "none_taken_legend": "No medications taken",
        "partial_taken_legend": "Missed some medications",
        "future_scheduled_legend": "Scheduled future doses",

        # Insulin History View
        "insulin_title": "Insulin History",
        "insulin_chart_title": "Insulin Chart",
        "insulin_line_graph": "Insulin Line Graph",
        "sugar_level": "Sugar level",
        "time": "Time",
        "insulin_taken_badge": "Insulin taken",
        "add_reading_btn": "+ Add Reading",
        "log_reading_modal_title": "Log Sugar Level & Time",
        "sugar_level_label": "Sugar Level (mmol/L)",
        "reading_time_label": "Reading Time",
        "reading_date_label": "Reading Date",
        "insulin_units_label": "Insulin Units (Optional)",
        "save_reading_btn": "SAVE READING",
        "no_readings_for_date": "No sugar level readings logged for this date.",
        "reading_saved_toast": "Sugar level {level} recorded at {time}!",
        "reading_deleted_toast": "Reading deleted.",

        # Caretaker Dashboard
        "no_patient_connected": "No Patient Connected",
        "connected": "Connected",
        "not_connected": "Not Connected",
        "attention": "ATTENTION",
        "all_patients_on_track": "All patients on track",
        "todays_schedule": "TODAY'S SCHEDULE",
        "dose_tracking_supply": "DOSE TRACKING & SUPPLY",
        "reschedule_attention_needed": "Action needed: stock is low or reschedule is due",
        "connect_patient_title": "Connect with Patient",
        "connect_patient_desc": "Enter 6-digit pairing code from patient",
        "pair_code_label": "Patient 6-digit code",
        "invalid_pairing_code": "Invalid or expired pairing code.",
        "already_paired_code": "This code has already been used.",
        "paired_success": "Successfully paired with {name}!",
        "take_on_behalf": "Mark Taken",
        "share_code_title": "Your Caregiver Pairing Code",
        "share_code_desc": "Share this 6-digit code with your caregiver",
        "tap_to_copy": "Tap to copy",
        "code_copied": "Code copied to clipboard!",
        "generating_code": "Generating code...",
        "pair_patient_btn": "+ Pair",
        "switch_patient": "Switch Patient",
        "view_all": "View All ›",
        "view_history": "View History ›",
        "manage_tracking": "Manage Tracking ›",
        "caretaker_hub_title": "PATIENT MANAGEMENT",
        "hub_prescriptions": "Prescriptions",
        "hub_dose_times": "Dose Times",
        "hub_adherence": "Adherence",
        "hub_blood_sugar": "Sugar & Insulin",

        # Medicines View
        "medicines_title": "Medicines",
        "your_medicines": "Your Medicines",
        "low_stock_filter": "Low Stock",
        "all_filter": "All",
        "filter_label": "FILTER : ",
        "add_btn": "ADD",
        "medicines_count": "{count} medicines",
        "medicine_count_single": "{count} medicine",
        "no_low_stock_found": "No low stock medicines found.",
        "no_meds_add_hint": "No medicines added yet. Tap ADD + above to add one!",
        "stock_chip": "Stock: {stock}",
        "out_of_stock_chip": "OUT",
        "days_left_chip": "{days}d left",
        "as_needed": "As needed",
        "doses_per_day": "{doses} doses/day",
        "restocked_toast": "Restocked 10 units for {name}!",
        "deleted_med_toast": "Deleted {name}.",
        "schedule_dose_tooltip": "Schedule Dose",
        "restock_tooltip": "Restock +10",
        "delete_tooltip": "Delete",
        "reschedule_refill_tooltip": "Reschedule / Refill",
        "add_medicine": "Add Medicine",
        "no_medicines_yet": "No medicines added yet.",
        "med_name_label": "MEDICATION NAME",
        "dosage_label": "DOSAGE",
        "form_label": "FORM",
        "disease_label": "DISEASE / CONDITION",
        "body_part_label": "BODY PART",
        "stock_label": "INITIAL STOCK",
        "restock_alert_label": "RESTOCK ALERT (DAYS)",
        "special_instructions_label": "SPECIAL INSTRUCTIONS / NOTES",
        "dose_frequency_label": "DOSE FREQUENCY",
        "schedule_times_label": "SCHEDULE TIMES",
        "dose_1_time": "Dose 1 Time",
        "dose_2_time": "Dose 2 Time",
        "dose_3_time": "Dose 3 Time",
        "select_days_label": "SELECT DAYS",
        "once_daily_opt": "Once daily (1 dose/day)",
        "twice_daily_opt": "Twice daily (2 doses/day)",
        "three_daily_opt": "Three times daily (3 doses/day)",
        "custom_days_opt": "Specific days of week",
        "save_medication": "Save Medication",
        "medication_saved": "Medication saved successfully!",
        "delete_confirm": "Are you sure you want to delete this medication?",

        # Schedule View
        "schedule_title": "Schedule",
        "dose_schedules_title": "Dose Schedules",
        "test_alarm_btn": "Test Alarm",
        "schedules_count": "{count} schedules",
        "schedule_count_single": "{count} schedule",
        "today": "Today",
        "no_schedules_today": "No dose schedules set for today.",
        "no_schedules_hint": "No dose schedules added yet. Tap ADD + above to schedule a dose!",
        "daily_tag": "Daily",
        "remove_schedule_toast": "Removed {time} schedule for {name}.",
        "delete_schedule_tooltip": "Delete Schedule",
        "schedule_dose_modal_title": "Schedule Dose",
        "no_meds_found_title": "No Medicines Found",
        "no_meds_found_desc": "Please add a medication first before creating a dose schedule.",
        "medication_label": "Medication",
        "dose_time_label": "Dose Time",
        "frequency_days_label": "Frequency / Days",
        "save_schedule_btn": "SAVE SCHEDULE",
        "preset_now": "Now",
        "preset_morning": "Morning (8am)",
        "preset_noon": "Noon (1pm)",
        "preset_night": "Night (9pm)",
        "freq_daily": "Daily (Every day)",
        "freq_weekdays": "Weekdays (Mon - Fri)",
        "freq_weekends": "Weekends (Sat - Sun)",
        "freq_custom": "Specific Days",
        "add_schedule_time": "Add Schedule Time",
        "morning": "Morning",
        "noon": "Noon",
        "night": "Night",
        "hour": "Hour",
        "minute": "Minute",
        "period": "Period",
        "schedule_added": "Schedule added!",
        "schedule_deleted": "Schedule removed.",

        # Language Toggle Button
        "toggle_to_bn": "🌐 বাংলা",
        "toggle_to_en": "🌐 English",
    },
    "bn": {
        # App / Navigation
        "app_title": "মেডিমেট",
        "nav_medicines": "ওষুধসমূহ",
        "nav_schedule": "সময়সূচী",
        "nav_history": "ইতিহাস",
        "nav_alerts": "সতর্কতা",
        "nav_profile": "প্রোফাইল",
        "logout": "লগআউট",
        "pairing_code": "পেয়ারিং কোড",
        "connect": "সংযুক্ত করুন",
        "close": "বন্ধ করুন",
        "cancel": "বাতিল",
        "save": "সংরক্ষণ",
        "delete": "মুছে ফেলুন",
        "edit": "সম্পাদনা",
        "back": "ফিরে যান",
        "all": "সব",
        "daily": "প্রতিদিন",
        "everyday": "প্রতিদিন",

        # Auth
        "sign_up": "সাইন আপ",
        "log_in": "লগইন",
        "sign_in_to_continue": "চালিয়ে যেতে সাইন ইন করুন।",
        "log_in_to_continue": "চালিয়ে যেতে লগইন করুন।",
        "already_have_account": "ইতিমধ্যে অ্যাকাউন্ট আছে? লগইন করুন",
        "signup_link": "নতুন অ্যাকাউন্ট খুলুন !",
        "name": "নাম",
        "role": "ভূমিকা",
        "email": "ইমেইল",
        "password": "পাসওয়ার্ড",
        "patient": "রোগী",
        "caretaker": "সেবাকারী",
        "name_hint": "যেমন: ঐশিকী সিথী",
        "email_hint": "যেমন: sithee123@gmail.com",
        "password_hint": "******",
        "all_fields_required": "সবগুলো তথ্য পূরণ করা আবশ্যক।",
        "email_password_required": "ইমেইল এবং পাসওয়ার্ড আবশ্যক।",
        "welcome_user": "স্বাগতম, {name}!",
        "welcome_back_user": "আবারও স্বাগতম, {name}!",

        # Header Greetings
        "good_morning": "শুভ সকাল, {name}",
        "good_afternoon": "শুভ অপরাহ্ন, {name}",
        "good_evening": "শুভ সন্ধ্যা, {name}",
        "hello_caregiver": "হ্যালো, সেবাকারী {name}",

        # Patient Dashboard
        "todays_medicines": "আজকের ওষুধসমূহ",
        "todays_progress": "আজকের অগ্রগতি",
        "doses_taken": "{taken} / {total} টি ডোজ সম্পন্ন",
        "meds_remaining": "{count} টি ওষুধ বাকি আছে",
        "meds_remaining_plural": "{count} টি ওষুধ বাকি আছে",
        "all_doses_complete": "আজকের সব ওষুধ খাওয়া সম্পন্ন! চমৎকার!",
        "no_meds_scheduled": "আজকের জন্য কোনো ওষুধ নির্ধারিত নেই",
        "take_now": "এখনই খান",
        "taken": "খেয়েছি",
        "snooze": "স্নুজ",
        "skip": "বাদ দিন",
        "missed": "মিস হয়েছে",
        "pending": "অপেক্ষমাণ",

        # Dose Tracking & Rescheduling
        "dose_tracking_reschedule": "ডোজ ট্র্যাকিং ও পুনঃনির্ধারণ",
        "dose_tracking_desc": "মজুদ, ব্যবহারের হার এবং সম্ভাব্য পুনঃনির্ধারণ তারিখ",
        "view_tracking_reschedule": "ডোজ ট্র্যাকিং ও পুনঃনির্ধারণ দেখুন",
        "tracking_subtitle": "মজুদ ব্যবহার ও স্বয়ংক্রিয় পুনঃনির্ধারণ পূর্বাভাস",
        "tab_schedules": "⏰ সময়সূচী",
        "tab_tracking": "🔄 ট্র্যাকিং ও পুনঃনির্ধারণ",
        "no_tracking_items": "এখনো কোনো ওষুধ ট্র্যাক করা হয়নি।",
        "stock": "মজুদ",
        "units": "টি",
        "pills": "টি ট্যাবলেট",
        "frequency": "মাত্রা",
        "days_supply_left": "দিনের সরবরাহ বাকি",
        "reschedule_due": "পুনঃনির্ধারণ তারিখ",
        "reschedule_now": "এখনই পুনঃনির্ধারণ",
        "reschedule_soon": "শীঘ্রই পুনঃনির্ধারণ",
        "supply_healthy": "মজুদ পর্যাপ্ত",
        "healthy_stock": "পর্যাপ্ত মজুদ",
        "reschedule_btn": "পুনঃনির্ধারণ",
        "immediate": "অবিলম্বে",
        "confirm_reschedule": "পুনঃনির্ধারণ নিশ্চিত করুন",
        "reschedule_refill_title": "পুনঃনির্ধারণ ও রিফিল: {name}",
        "current_stock_label": "বর্তমান মজুদ: {stock} টি",
        "frequency_label": "মাত্রা: {freq}",
        "supply_remaining_label": "অবশিষ্ট সরবরাহ: {days} দিন",
        "projected_reschedule_label": "সম্ভাব্য পুনঃনির্ধারণ: {date}",
        "added_stock_label": "যোগকৃত মজুদ (টি / বড়ি)",
        "rescheduled_toast": "{name} পুনঃনির্ধারণ সম্পন্ন! +{qty} টি মজুদ যোগ হয়েছে।",
        "reschedule_failed": "পুনঃনির্ধারণ ব্যর্থ হয়েছে: {err}",

        # Hamburger Dropdown Menu
        "menu_dashboard": "ড্যাশবোর্ড",
        "menu_schedules": "ডোজের সময়সূচী",
        "menu_tracking": "ডোজ ট্র্যাকিং ও পুনঃনির্ধারণ",
        "menu_medicines": "সকল ওষুধ",
        "menu_insulin": "ইনসুলিনের ইতিহাস",
        "menu_pairing": "পেয়ারিং কোড",
        "menu_history": "ওষুধের ইতিহাস",
        "menu_profile": "প্রোফাইল",
        "menu_logout": "লগআউট",

        # Profile Card
        "profile_patient_title": "রোগীর প্রোফাইল",
        "profile_caregiver_title": "কেয়ারগিভার প্রোফাইল",
        "profile_health_vitals": "স্বাস্থ্য ও চিকিৎসার তথ্য",
        "profile_blood_group": "রক্তের গ্রুপ",
        "profile_age_gender": "বয়স ও লিঙ্গ",
        "profile_weight_height": "ওজন ও উচ্চতা",
        "profile_emergency_phone": "জরুরি যোগাযোগ",
        "profile_allergies_conditions": "অ্যালার্জি ও শারীরিক অবস্থা",
        "profile_pairing_code": "কেয়ারগিভার পেয়ারিং কোড",
        "profile_linked_patient": "সংযুক্ত রোগী",
        "profile_generate_code": "কোড তৈরি করুন",
        "profile_connect_patient": "রোগী যুক্ত করুন",
        "profile_edit_btn": "তথ্য পরিবর্তন",
        "profile_edit_title": "স্বাস্থ্য তথ্য পরিবর্তন করুন",
        "profile_save_btn": "তথ্য সংরক্ষণ করুন",
        "profile_logout_btn": "লগ আউট",
        "profile_years_old": "বছর",
        "profile_updated_toast": "প্রোফাইলের তথ্য সফলভাবে সংরক্ষিত হয়েছে!",

        # History View
        "history_title": "ইতিহাস",
        "history_calendar_title": "ইতিহাসের ক্যালেন্ডার",
        "no_doses_on_date": "এই তারিখে কোনো ওষুধ নির্ধারিত নেই।",
        "all_taken_legend": "সব ওষুধ খাওয়া হয়েছে",
        "none_taken_legend": "কোনো ওষুধ খাওয়া হয়নি",
        "partial_taken_legend": "কিছু ওষুধ মিস হয়েছে",
        "future_scheduled_legend": "ভবিষ্যতের নির্ধারিত ডোজ",

        # Insulin History View
        "insulin_title": "ইনসুলিনের ইতিহাস",
        "insulin_chart_title": "ইনসুলিন চার্ট",
        "insulin_line_graph": "ইনসুলিন লাইন গ্রাফ",
        "sugar_level": "সুগার লেভেল",
        "time": "সময়",
        "insulin_taken_badge": "ইনসুলিন গ্রহণ",
        "add_reading_btn": "+ পরিমাপ যোগ করুন",
        "log_reading_modal_title": "সুগার লেভেল ও সময় সংরক্ষণ",
        "sugar_level_label": "সুগার লেভেল (mmol/L)",
        "reading_time_label": "পরিমাপের সময়",
        "reading_date_label": "পরিমাপের তারিখ",
        "insulin_units_label": "ইনসুলিন ইউনিট (ঐচ্ছিক)",
        "save_reading_btn": "পরিমাপ সংরক্ষণ করুন",
        "no_readings_for_date": "এই তারিখের জন্য কোনো সুগার লেভেলের পরিমাপ নেই।",
        "reading_saved_toast": "সুগার লেভেল {level} ({time}) সংরক্ষিত হয়েছে!",
        "reading_deleted_toast": "পরিমাপ মুছে ফেলা হয়েছে।",

        # Caretaker Dashboard
        "no_patient_connected": "কোনো রোগী সংযুক্ত নেই",
        "connected": "সংযুক্ত",
        "not_connected": "সংযুক্ত নয়",
        "attention": "দৃষ্টি আকর্ষণ",
        "all_patients_on_track": "সব রোগী সময়মতো ওষুধ নিচ্ছেন",
        "todays_schedule": "আজকের সময়সূচী",
        "dose_tracking_supply": "ডোজ ট্র্যাকিং ও সরবরাহ",
        "reschedule_attention_needed": "দৃষ্টি আকর্ষণ: মজুদ কম বা পুনঃনির্ধারণ প্রয়োজন",
        "connect_patient_title": "রোগীর সাথে যুক্ত হন",
        "connect_patient_desc": "রোগীর কাছ থেকে পাওয়া ৬-সংখ্যার কোড লিখুন",
        "pair_code_label": "রোগীর ৬-সংখ্যার কোড",
        "invalid_pairing_code": "অবৈধ বা মেয়াদোত্তীর্ণ পেয়ারিং কোড।",
        "already_paired_code": "এই কোডটি ইতিমধ্যে ব্যবহৃত হয়েছে।",
        "paired_success": "{name}-এর সাথে সফলভাবে যুক্ত হয়েছে!",
        "take_on_behalf": "গ্রহণ চিহ্নিত করুন",
        "share_code_title": "আপনার কেয়ারগিভার পেয়ারিং কোড",
        "share_code_desc": "আপনার কেয়ারগিভারের সাথে এই ৬-সংখ্যার কোডটি শেয়ার করুন",
        "tap_to_copy": "কপি করতে ট্যাপ করুন",
        "code_copied": "কোড ক্লিপবোর্ডে কপি হয়েছে!",
        "generating_code": "কোড তৈরি হচ্ছে...",
        "pair_patient_btn": "+ যুক্ত করুন",
        "switch_patient": "রোগী পরিবর্তন",
        "view_all": "সব দেখুন ›",
        "view_history": "ইতিহাস দেখুন ›",
        "manage_tracking": "ট্র্যাকিং পরিচালনা ›",
        "caretaker_hub_title": "রোগী ব্যবস্থাপনা",
        "hub_prescriptions": "প্রেসক্রিপশন ও মজুদ",
        "hub_dose_times": "ডোজের সময়সূচী",
        "hub_adherence": "পালন ক্যালেন্ডার",
        "hub_blood_sugar": "সুগার ও ইনসুলিন",

        # Medicines View
        "medicines_title": "ওষুধসমূহ",
        "your_medicines": "আপনার ওষুধসমূহ",
        "low_stock_filter": "কম মজুদ",
        "all_filter": "সব",
        "filter_label": "ফিল্টার : ",
        "add_btn": "যোগ",
        "medicines_count": "{count} টি ওষুধ",
        "medicine_count_single": "{count} টি ওষুধ",
        "no_low_stock_found": "কম মজুদের কোনো ওষুধ পাওয়া যায়নি।",
        "no_meds_add_hint": "এখনো কোনো ওষুধ যোগ করা হয়নি। উপরে ADD + চাপুন!",
        "stock_chip": "মজুদ: {stock}",
        "out_of_stock_chip": "মজুদ শেষ",
        "days_left_chip": "{days} দিন বাকি",
        "as_needed": "প্রয়োজনমতো",
        "doses_per_day": "দিনে {doses}টি ডোজ",
        "restocked_toast": "{name}-এর জন্য ১০টি মজুদ যোগ করা হয়েছে!",
        "deleted_med_toast": "{name} মুছে ফেলা হয়েছে।",
        "schedule_dose_tooltip": "সময়সূচী যোগ করুন",
        "restock_tooltip": "রিস্টক +১০",
        "delete_tooltip": "মুছে ফেলুন",
        "reschedule_refill_tooltip": "পুনঃনির্ধারণ / রিফিল",
        "add_medicine": "ওষুধ যোগ করুন",
        "no_medicines_yet": "এখনো কোনো ওষুধ যোগ করা হয়নি।",
        "med_name_label": "ওষুধের নাম",
        "dosage_label": "ডোজের পরিমাণ",
        "form_label": "ধরন",
        "disease_label": "রোগ / উপসর্গ",
        "body_part_label": "শরীরের অঙ্গ",
        "stock_label": "প্রাথমিক মজুদ",
        "restock_alert_label": "রিস্টক সতর্কতা (কত দিন আগে)",
        "special_instructions_label": "বিশেষ নির্দেশাবলী বা মন্তব্য",
        "dose_frequency_label": "ডোজের মাত্রা",
        "schedule_times_label": "সময়সূচী",
        "dose_1_time": "১ম ডোজের সময়",
        "dose_2_time": "২য় ডোজের সময়",
        "dose_3_time": "৩য় ডোজের সময়",
        "select_days_label": "দিন নির্বাচন করুন",
        "once_daily_opt": "দিনে ১ বার (১টি ডোজ)",
        "twice_daily_opt": "দিনে ২ বার (২টি ডোজ)",
        "three_daily_opt": "দিনে ৩ বার (৩টি ডোজ)",
        "custom_days_opt": "সপ্তাহের নির্দিষ্ট দিন",
        "save_medication": "ওষুধ সংরক্ষণ করুন",
        "medication_saved": "ওষুধ সফলভাবে সংরক্ষিত হয়েছে!",
        "delete_confirm": "আপনি কি নিশ্চিতভাবে এই ওষুধটি মুছে ফেলতে চান?",

        # Schedule View
        "schedule_title": "সময়সূচী",
        "dose_schedules_title": "ডোজের সময়সূচী",
        "test_alarm_btn": "টেস্ট অ্যালার্ম",
        "schedules_count": "{count} টি সময়সূচী",
        "schedule_count_single": "{count} টি সময়সূচী",
        "today": "আজ",
        "no_schedules_today": "আজকের জন্য কোনো ডোজের সময়সূচী নেই।",
        "no_schedules_hint": "এখনো কোনো সময়সূচী যোগ করা হয়নি। উপরে ADD + ট্যাপ করে সময় নির্ধারণ করুন!",
        "daily_tag": "প্রতিদিন",
        "remove_schedule_toast": "{name}-এর {time} সময়সূচী মুছে ফেলা হয়েছে।",
        "delete_schedule_tooltip": "সময়সূচী মুছুন",
        "schedule_dose_modal_title": "ডোজের সময় নির্ধারণ",
        "no_meds_found_title": "কোনো ওষুধ পাওয়া যায়নি",
        "no_meds_found_desc": "ডোজ নির্ধারণ করার আগে দয়া করে একটি ওষুধ যোগ করুন।",
        "medication_label": "ওষুধ",
        "dose_time_label": "ডোজের সময়",
        "frequency_days_label": "মাত্রা ও দিনসমূহ",
        "save_schedule_btn": "সময়সূচী সংরক্ষণ",
        "preset_now": "এখন",
        "preset_morning": "সকাল (৮টা)",
        "preset_noon": "দুপুর (১টা)",
        "preset_night": "রাত (৯টা)",
        "freq_daily": "প্রতিদিন (সব দিন)",
        "freq_weekdays": "কাজের দিন (সোম - শুক্র)",
        "freq_weekends": "ছুটির দিন (শনি - রবি)",
        "freq_custom": "নির্দিষ্ট দিন",
        "add_schedule_time": "নতুন সময় যোগ করুন",
        "morning": "সকাল",
        "noon": "দুপুর",
        "night": "রাত",
        "hour": "ঘণ্টা",
        "minute": "মিনিট",
        "period": "সময়কাল",
        "schedule_added": "সময়সূচী যোগ হয়েছে!",
        "schedule_deleted": "সময়সূচী মুছে ফেলা হয়েছে।",

        # Language Toggle Button
        "toggle_to_bn": "🌐 বাংলা",
        "toggle_to_en": "🌐 English",
    },
}


def get_current_language() -> str:
    """Return the active language code ('en' or 'bn')."""
    return _current_language


def set_language(lang: str, notify: bool = True) -> None:
    """Set the active language ('en' or 'bn') and notify all registered listeners."""
    global _current_language
    cleaned = lang.lower().strip()
    if cleaned not in ("en", "bn"):
        cleaned = "en"
    if _current_language != cleaned:
        _current_language = cleaned
        if notify:
            _notify_listeners(cleaned)


def toggle_language(notify: bool = True) -> str:
    """Interchange language between English and Bangla with a single invocation."""
    new_lang = "bn" if _current_language == "en" else "en"
    set_language(new_lang, notify=notify)
    return new_lang


def get_toggle_button_label() -> str:
    """Label shown on the toggle button indicating what clicking will switch to.

    When current language is 'en', button offers '🌐 বাংলা'.
    When current language is 'bn', button offers '🌐 English'.
    """
    return "🌐 বাংলা" if _current_language == "en" else "🌐 English"


def t(key: str, **kwargs: Any) -> str:
    """Translate a key into the currently active language with optional format kwargs."""
    lang_dict = TRANSLATIONS.get(_current_language, TRANSLATIONS["en"])
    template = lang_dict.get(key)
    if template is None:
        template = TRANSLATIONS["en"].get(key, key)
    if kwargs:
        try:
            return template.format(**kwargs)
        except Exception:
            return template
    return template


def register_language_listener(callback: Callable[[str], None]) -> None:
    """Register a UI listener callback to be invoked when the language changes."""
    if callback not in _listeners:
        _listeners.append(callback)


def unregister_language_listener(callback: Callable[[str], None]) -> None:
    """Unregister a previously registered UI language listener."""
    if callback in _listeners:
        _listeners.remove(callback)


def _notify_listeners(lang: str) -> None:
    for listener in list(_listeners):
        try:
            listener(lang)
        except Exception as exc:
            logger.debug("Language listener error: %s", exc)
