const DUMMY: Record<string, string> = {
  FIRST_NAME: "Rahul",
  LAST_NAME: "Sharma",
  NAME: "Rahul Sharma",
  FULL_NAME: "Rahul Sharma",
  LOCATION: "Mumbai",
  CITY: "Mumbai",
  EMAIL: "rahul.sharma@example.com",
  PHONE: "+91 98765 43210",
  COMPANY: "Infosys Ltd.",
  OCCUPATION: "Software Engineer",
  CREDIT_SCORE: "762",
  INCOME: "₹85,000",
};

export function fillPlaceholders(text: string): string {
  return text.replace(/\[([A-Z_]+)\]/g, (match, key: string) => DUMMY[key] ?? match);
}

export function stripHtml(html: string): string {
  return html.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
}
