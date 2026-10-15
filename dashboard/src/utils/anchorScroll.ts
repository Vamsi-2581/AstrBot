export function scrollToAnchorWithin(
  event: MouseEvent,
  container: HTMLElement | null,
): void {
  const targetElement = event.target instanceof Element ? event.target : null;
  const anchor = targetElement?.closest('a[href^="#"]');
  if (!anchor) return;

  const rawHref = anchor.getAttribute('href');
  const targetId = rawHref ? decodeURIComponent(rawHref.slice(1)) : '';
  if (!targetId) return;

  const target = container?.querySelector(`#${CSS.escape(targetId)}`);
  if (!target) return;

  event.preventDefault();
  target.scrollIntoView({ behavior: 'smooth', block: 'start' });
}
