// Legal pages. Templates until counsel reviews them: each page says so at the top.
export interface LegalPage {
  title: string;
  paragraphs: readonly string[];
}

export const LEGAL_PAGES: Record<string, LegalPage> = {
  terms: {
    title: "Terms of use",
    paragraphs: [
      "This website describes a business-to-business service. Using it does not create a contract; any service is provided only under a signed agreement with its own terms.",
      "Content is provided for information. Numbers on this site are sourced, measured on test data with their method and date, or labelled as estimates.",
      "You may not attempt to access private pages without a passcode, probe the service for vulnerabilities outside our disclosure policy, or use the site to send unsolicited messages.",
      "The site is provided as is. To the extent the law allows, we exclude liability for loss arising from use of the site. These terms are governed by the laws of India.",
    ],
  },
  privacy: {
    title: "Privacy notice",
    paragraphs: [
      "This notice covers this website. When we process a client's customers' data, we do so as a processor under the client's instructions and a data processing agreement; the client's notice applies to those customers.",
      "On this site we collect what you choose to give us: your name, work email and message when you book a call or write to us, and the questions you type into the site assistant. We use them only to reply and to arrange the call, and keep them for 12 months unless you ask us to delete them sooner.",
      "We do not use advertising cookies or third-party trackers. Server logs keep IP addresses for security for up to 180 days.",
      "You can ask to access, correct or erase your data, or withdraw consent, by writing to the contact on the company page. You may also complain to the Data Protection Board of India.",
    ],
  },
  dpa: {
    title: "Data processing agreement",
    paragraphs: [
      "Clients sign a data processing agreement before any personal data is shared. It is drafted against the Digital Personal Data Protection Act 2023 and Rules 2025.",
      "Its main terms: processing only for the agreed purposes and on the client's instructions; no use for model training; India residency by default; sub-processor changes with 30 days' notice; breach notice to the client within 24 hours; deletion within 30 days of termination.",
      "A copy of the template is available on request.",
    ],
  },
  subprocessors: {
    title: "Sub-processors",
    paragraphs: [
      "For each client we use one provider per role: speech to text, text to speech, a language model, telephony, WhatsApp, and the client's CRM. None may train on client data.",
      "The default region is India. The service refuses to start if a configured provider's region is outside the client's allowed list.",
      "The current list with regions is part of each client's data processing agreement; changes are notified 30 days in advance.",
    ],
  },
  aup: {
    title: "Acceptable use",
    paragraphs: [
      "The service places service and transactional calls only. It may not be used for promotional calls without the declared number series, recorded promotional consent and an audit the law requires.",
      "Clients may not use it to call numbers without a lawful consent basis, to collect card details, PINs or one-time passwords, to impersonate a person, or to clone a real person's voice.",
      "We may suspend service immediately to stop a call that would break these rules or the law, and will tell the client why.",
    ],
  },
};
