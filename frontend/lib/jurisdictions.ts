import countries from "i18n-iso-countries";
import enLocale from "i18n-iso-countries/langs/en.json";

countries.registerLocale(enLocale);

// Common subdivision names (ISO 3166-2) that appear frequently in LEI data
const SUBDIVISIONS: Record<string, string> = {
  "US-AL": "Alabama", "US-AK": "Alaska", "US-AZ": "Arizona", "US-AR": "Arkansas",
  "US-CA": "California", "US-CO": "Colorado", "US-CT": "Connecticut", "US-DE": "Delaware",
  "US-FL": "Florida", "US-GA": "Georgia", "US-HI": "Hawaii", "US-ID": "Idaho",
  "US-IL": "Illinois", "US-IN": "Indiana", "US-IA": "Iowa", "US-KS": "Kansas",
  "US-KY": "Kentucky", "US-LA": "Louisiana", "US-ME": "Maine", "US-MD": "Maryland",
  "US-MA": "Massachusetts", "US-MI": "Michigan", "US-MN": "Minnesota", "US-MS": "Mississippi",
  "US-MO": "Missouri", "US-MT": "Montana", "US-NE": "Nebraska", "US-NV": "Nevada",
  "US-NH": "New Hampshire", "US-NJ": "New Jersey", "US-NM": "New Mexico", "US-NY": "New York",
  "US-NC": "North Carolina", "US-ND": "North Dakota", "US-OH": "Ohio", "US-OK": "Oklahoma",
  "US-OR": "Oregon", "US-PA": "Pennsylvania", "US-RI": "Rhode Island", "US-SC": "South Carolina",
  "US-SD": "South Dakota", "US-TN": "Tennessee", "US-TX": "Texas", "US-UT": "Utah",
  "US-VT": "Vermont", "US-VA": "Virginia", "US-WA": "Washington", "US-WV": "West Virginia",
  "US-WI": "Wisconsin", "US-WY": "Wyoming", "US-DC": "District of Columbia",
  // Canadian provinces
  "CA-AB": "Alberta", "CA-BC": "British Columbia", "CA-MB": "Manitoba",
  "CA-NB": "New Brunswick", "CA-NL": "Newfoundland", "CA-NS": "Nova Scotia",
  "CA-ON": "Ontario", "CA-PE": "Prince Edward Island", "CA-QC": "Quebec",
  "CA-SK": "Saskatchewan", "CA-NT": "Northwest Territories", "CA-NU": "Nunavut", "CA-YT": "Yukon",
  // Australian states
  "AU-NSW": "New South Wales", "AU-VIC": "Victoria", "AU-QLD": "Queensland",
  "AU-WA": "Western Australia", "AU-SA": "South Australia", "AU-TAS": "Tasmania",
  "AU-ACT": "Australian Capital Territory", "AU-NT": "Northern Territory",
};

/**
 * Resolves a GLEIF jurisdiction code to a human-readable name.
 *
 * - "DE"    → "Germany"
 * - "US-DE" → "United States · Delaware"
 * - "XY"    → "XY" (unknown, returned as-is)
 */
export function jurisdictionName(code: string): string {
  if (!code) return "—";

  // Subdivision code (e.g. "US-DE")
  if (code.includes("-")) {
    const known = SUBDIVISIONS[code];
    if (known) {
      const countryCode = code.split("-")[0];
      const countryName = countries.getName(countryCode, "en");
      return countryName ? `${countryName} · ${known}` : `${countryCode} · ${known}`;
    }
    // Unknown subdivision — show "Country · CODE" if we know the country
    const [countryCode, sub] = code.split("-");
    const countryName = countries.getName(countryCode, "en");
    return countryName ? `${countryName} · ${sub}` : code;
  }

  // Plain country code
  return countries.getName(code, "en") ?? code;
}
