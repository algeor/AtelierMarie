"use client";

import { useCallback, useState, type FormEvent } from "react";
import { useLocale, useTranslations } from "next-intl";
import { submitContact } from "@/lib/api";
import { ApiError } from "@/lib/api-client";
import { useLocalizedError } from "@/lib/useLocalizedError";
import { Button } from "@/components/ui/Button";
import type { Locale } from "@/i18n/routing";

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MAX_NAME_LENGTH = 100;
const MAX_EMAIL_LENGTH = 254;
const MAX_MESSAGE_LENGTH = 2000;

type FieldErrors = Partial<Record<"name" | "email" | "message", string>>;

export function ContactForm() {
  const t = useTranslations("contact");
  const locale = useLocale() as Locale;
  const getLocalizedError = useLocalizedError();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [website, setWebsite] = useState("");
  const [errors, setErrors] = useState<FieldErrors>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const validate = useCallback((): FieldErrors => {
    const next: FieldErrors = {};
    if (!name.trim()) next.name = t("nameRequired");
    else if (name.trim().length > MAX_NAME_LENGTH) next.name = t("nameTooLong");

    if (!email.trim()) next.email = t("emailRequired");
    else if (email.trim().length > MAX_EMAIL_LENGTH) next.email = t("emailTooLong");
    else if (!EMAIL_REGEX.test(email.trim())) next.email = t("emailInvalid");

    if (!message.trim()) next.message = t("messageRequired");
    else if (message.trim().length > MAX_MESSAGE_LENGTH) next.message = t("messageTooLong");
    return next;
  }, [email, message, name, t]);

  const handleSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      setSubmitError(null);
      setIsSuccess(false);

      const nextErrors = validate();
      setErrors(nextErrors);
      if (Object.keys(nextErrors).length > 0) return;

      setIsSubmitting(true);
      try {
        await submitContact({
          name: name.trim(),
          email: email.trim(),
          message: message.trim(),
          locale,
          website: website.trim(),
        });
        setName("");
        setEmail("");
        setMessage("");
        setWebsite("");
        setErrors({});
        setIsSuccess(true);
      } catch (error) {
        if (error instanceof ApiError) {
          setSubmitError(getLocalizedError(error.code));
        } else {
          setSubmitError(t("genericError"));
        }
      } finally {
        setIsSubmitting(false);
      }
    },
    [email, getLocalizedError, locale, message, name, t, validate, website],
  );

  return (
    <form onSubmit={handleSubmit} noValidate className="rounded-brand border border-champagne-beige bg-warm-ivory p-5 sm:p-6">
      <div aria-live="polite" className="mb-5 min-h-[1px]">
        {isSuccess && (
          <p className="rounded-brand border border-muted-gold/40 bg-cream px-4 py-3 text-sm text-charcoal">
            {t("success")}
          </p>
        )}
        {submitError && (
          <p className="rounded-brand border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {submitError}
          </p>
        )}
      </div>

      <div className="hidden" aria-hidden="true">
        <label htmlFor="contact-website">Website</label>
        <input
          id="contact-website"
          name="website"
          type="text"
          tabIndex={-1}
          autoComplete="off"
          value={website}
          onChange={(event) => setWebsite(event.target.value)}
        />
      </div>

      <div className="mb-5">
        <label htmlFor="contact-name" className="mb-1.5 block text-sm font-medium text-soft-brown">
          {t("name")} <span className="text-red-700">*</span>
        </label>
        <input
          id="contact-name"
          type="text"
          value={name}
          maxLength={MAX_NAME_LENGTH}
          onChange={(event) => setName(event.target.value)}
          aria-required="true"
          aria-invalid={errors.name ? "true" : undefined}
          aria-describedby={errors.name ? "contact-name-error" : undefined}
          className={`w-full rounded-brand border bg-warm-ivory px-4 py-3 text-charcoal placeholder:text-soft-brown/50 focus:outline-none focus:ring-2 focus:ring-soft-brown focus:ring-offset-2 focus:ring-offset-warm-ivory ${
            errors.name ? "border-red-700" : "border-champagne-beige"
          }`}
          placeholder={t("namePlaceholder")}
        />
        {errors.name && (
          <p id="contact-name-error" className="mt-1.5 text-sm text-red-700">
            {errors.name}
          </p>
        )}
      </div>

      <div className="mb-5">
        <label htmlFor="contact-email" className="mb-1.5 block text-sm font-medium text-soft-brown">
          {t("email")} <span className="text-red-700">*</span>
        </label>
        <input
          id="contact-email"
          type="email"
          value={email}
          maxLength={MAX_EMAIL_LENGTH}
          onChange={(event) => setEmail(event.target.value)}
          aria-required="true"
          aria-invalid={errors.email ? "true" : undefined}
          aria-describedby={errors.email ? "contact-email-error" : undefined}
          className={`w-full rounded-brand border bg-warm-ivory px-4 py-3 text-charcoal placeholder:text-soft-brown/50 focus:outline-none focus:ring-2 focus:ring-soft-brown focus:ring-offset-2 focus:ring-offset-warm-ivory ${
            errors.email ? "border-red-700" : "border-champagne-beige"
          }`}
          placeholder={t("emailPlaceholder")}
        />
        {errors.email && (
          <p id="contact-email-error" className="mt-1.5 text-sm text-red-700">
            {errors.email}
          </p>
        )}
      </div>

      <div className="mb-6">
        <label htmlFor="contact-message" className="mb-1.5 block text-sm font-medium text-soft-brown">
          {t("message")} <span className="text-red-700">*</span>
        </label>
        <textarea
          id="contact-message"
          rows={6}
          value={message}
          maxLength={MAX_MESSAGE_LENGTH}
          onChange={(event) => setMessage(event.target.value)}
          aria-required="true"
          aria-invalid={errors.message ? "true" : undefined}
          aria-describedby={errors.message ? "contact-message-error" : "contact-message-help"}
          className={`w-full resize-y rounded-brand border bg-warm-ivory px-4 py-3 text-charcoal placeholder:text-soft-brown/50 focus:outline-none focus:ring-2 focus:ring-soft-brown focus:ring-offset-2 focus:ring-offset-warm-ivory ${
            errors.message ? "border-red-700" : "border-champagne-beige"
          }`}
          placeholder={t("messagePlaceholder")}
        />
        {errors.message ? (
          <p id="contact-message-error" className="mt-1.5 text-sm text-red-700">
            {errors.message}
          </p>
        ) : (
          <p id="contact-message-help" className="mt-1.5 text-sm text-soft-brown/70">
            {t("messageHelp")}
          </p>
        )}
      </div>

      <Button type="submit" size="lg" isLoading={isSubmitting} className="w-full sm:w-auto">
        {isSubmitting ? t("submitting") : t("submit")}
      </Button>
    </form>
  );
}
