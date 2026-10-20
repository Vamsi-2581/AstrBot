import { defineComponent, h } from 'vue';
import { VIcon } from 'vuetify/components';

function icon(name: string) {
  return defineComponent({
    name: `TraceIcon${name.replace(/[^a-z0-9]/gi, '')}`,
    props: { size: { type: [Number, String], default: 16 } },
    setup(props, { attrs }) {
      return () => h(VIcon, { ...attrs, icon: name, size: props.size });
    },
  });
}

export const Activity = icon('mdi-pulse');
export const Bot = icon('mdi-robot-outline');
export const Box = icon('mdi-package-variant-closed');
export const Check = icon('mdi-check');
export const ChevronDown = icon('mdi-chevron-down');
export const Clock3 = icon('mdi-clock-outline');
export const Hash = icon('mdi-pound');
export const Heart = icon('mdi-heart-outline');
export const LoaderCircle = icon('mdi-loading');
export const Pause = icon('mdi-pause');
export const Play = icon('mdi-play');
export const PlugZap = icon('mdi-flash');
export const Puzzle = icon('mdi-puzzle');
export const RefreshCw = icon('mdi-refresh');
export const Search = icon('mdi-magnify');
export const Send = icon('mdi-send');
export const UserRound = icon('mdi-account');
export const Workflow = icon('mdi-sitemap');
export const Wrench = icon('mdi-wrench');
export const X = icon('mdi-close');
