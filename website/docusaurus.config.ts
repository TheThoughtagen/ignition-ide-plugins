import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'Ignition Dev Tools',
  tagline: 'Multi-editor IDE support for Ignition SCADA',
  favicon: 'img/favicon.ico',

  future: {
    v4: true,
  },

  url: 'https://pmannion2.github.io',
  baseUrl: '/ignition-nvim/',

  organizationName: 'pmannion2',
  projectName: 'ignition-nvim',

  onBrokenLinks: 'warn',

  markdown: {
    format: 'md',
    hooks: {
      onBrokenMarkdownLinks: 'warn',
    },
  },

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          path: '../docs',
          sidebarPath: './sidebars.ts',
          editUrl:
            'https://github.com/pmannion2/ignition-nvim/tree/main/docs/',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    colorMode: {
      defaultMode: 'dark',
      disableSwitch: false,
      respectPrefersColorScheme: false,
    },
    navbar: {
      title: 'Ignition Dev Tools',
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'docsSidebar',
          position: 'left',
          label: 'Docs',
        },
        {
          href: 'https://github.com/pmannion2/ignition-nvim',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Documentation',
          items: [
            {label: 'Getting Started', to: '/docs/getting-started/installation'},
            {label: 'Guides', to: '/docs/guides/commands'},
            {label: 'Configuration', to: '/docs/configuration/options'},
          ],
        },
        {
          title: 'Guides',
          items: [
            {label: 'Script Editing', to: '/docs/guides/script-editing'},
            {label: 'LSP Features', to: '/docs/guides/lsp-features'},
            {label: 'Kindling', to: '/docs/guides/kindling'},
          ],
        },
        {
          title: 'Claude Code Plugin',
          items: [
            {label: 'Overview', to: '/docs/claude-code-plugin/overview'},
            {label: 'Testing', to: '/docs/claude-code-plugin/testing'},
            {label: 'Skills Reference', to: '/docs/claude-code-plugin/skills-reference'},
          ],
        },
        {
          title: 'More',
          items: [
            {
              label: 'GitHub',
              href: 'https://github.com/pmannion2/ignition-nvim',
            },
            {
              label: 'ignition-lint',
              href: 'https://pmannion2.github.io/ignition-lint/',
            },
            {
              label: 'Credits',
              to: '/docs/credits',
            },
          ],
        },
      ],
      copyright: `Copyright &copy; ${new Date().getFullYear()} Whiskey House Labs. Built with Docusaurus.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['bash', 'json', 'yaml', 'python', 'lua', 'typescript'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
