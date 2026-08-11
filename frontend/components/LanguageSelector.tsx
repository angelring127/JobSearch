'use client';

import { FlagCa, FlagCn, FlagJp, FlagKr } from '@sankyu/react-circle-flags';
import {
  useEffect,
  useId,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
} from 'react';
import { LANGUAGE_OPTIONS, type Locale } from '@/lib/i18n';

type LanguageSelectorProps = {
  label: string;
  locale: Locale;
  onChange: (locale: Locale) => void;
};

function LanguageFlag({ locale, size }: { locale: Locale; size: number }) {
  const props = {
    'aria-hidden': true,
    className: 'language-flag',
    focusable: false,
    height: size,
    width: size,
  } as const;

  if (locale === 'ko') return <FlagKr {...props} />;
  if (locale === 'en') return <FlagCa {...props} />;
  if (locale === 'ja') return <FlagJp {...props} />;
  return <FlagCn {...props} />;
}

export default function LanguageSelector({ label, locale, onChange }: LanguageSelectorProps) {
  const [open, setOpen] = useState(false);
  const menuId = useId();
  const wrapperRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const itemRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const activeIndex = Math.max(0, LANGUAGE_OPTIONS.findIndex((option) => option.value === locale));
  const activeLanguage = LANGUAGE_OPTIONS[activeIndex];

  useEffect(() => {
    if (!open) return;

    itemRefs.current[activeIndex]?.focus();

    const handlePointerDown = (event: PointerEvent) => {
      if (!wrapperRef.current?.contains(event.target as Node)) setOpen(false);
    };

    document.addEventListener('pointerdown', handlePointerDown);
    return () => document.removeEventListener('pointerdown', handlePointerDown);
  }, [activeIndex, open]);

  const closeAndFocusTrigger = () => {
    setOpen(false);
    window.requestAnimationFrame(() => triggerRef.current?.focus());
  };

  const selectLocale = (nextLocale: Locale) => {
    onChange(nextLocale);
    closeAndFocusTrigger();
  };

  const focusItem = (index: number) => {
    const nextIndex = (index + LANGUAGE_OPTIONS.length) % LANGUAGE_OPTIONS.length;
    itemRefs.current[nextIndex]?.focus();
  };

  const handleItemKeyDown = (event: ReactKeyboardEvent<HTMLButtonElement>, index: number) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      focusItem(index + 1);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      focusItem(index - 1);
    } else if (event.key === 'Home') {
      event.preventDefault();
      focusItem(0);
    } else if (event.key === 'End') {
      event.preventDefault();
      focusItem(LANGUAGE_OPTIONS.length - 1);
    } else if (event.key === 'Escape') {
      event.preventDefault();
      closeAndFocusTrigger();
    } else if (event.key === 'Tab') {
      setOpen(false);
    }
  };

  return (
    <div
      ref={wrapperRef}
      className="language-select"
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false);
      }}
    >
      <button
        ref={triggerRef}
        type="button"
        className="language-select__trigger"
        aria-label={`${label}: ${activeLanguage.country}, ${activeLanguage.language}`}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        title={`${label}: ${activeLanguage.country} · ${activeLanguage.language}`}
        onClick={() => setOpen((current) => !current)}
        onKeyDown={(event) => {
          if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
            event.preventDefault();
            setOpen(true);
          } else if (event.key === 'Escape' && open) {
            event.preventDefault();
            setOpen(false);
          }
        }}
      >
        <LanguageFlag locale={locale} size={32} />
        <span className="language-select__chevron" aria-hidden="true">
          <svg viewBox="0 0 12 12">
            <path d="m3.5 4.75 2.5 2.5 2.5-2.5" />
          </svg>
        </span>
      </button>

      {open ? (
        <div id={menuId} className="language-menu" role="menu" aria-label={label}>
          {LANGUAGE_OPTIONS.map((option, index) => {
            const selected = option.value === locale;

            return (
              <button
                key={option.value}
                ref={(element) => {
                  itemRefs.current[index] = element;
                }}
                type="button"
                className="language-menu__option"
                role="menuitemradio"
                aria-checked={selected}
                onClick={() => selectLocale(option.value)}
                onKeyDown={(event) => handleItemKeyDown(event, index)}
              >
                <LanguageFlag locale={option.value} size={30} />
                <span className="language-menu__copy">
                  <span className="language-menu__country">{option.country}</span>
                  <span className="language-menu__language">{option.language}</span>
                </span>
                <span className="language-menu__check" aria-hidden="true">
                  {selected ? (
                    <svg viewBox="0 0 16 16">
                      <path d="m3.5 8.25 2.75 2.75 6.25-6.25" />
                    </svg>
                  ) : null}
                </span>
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
