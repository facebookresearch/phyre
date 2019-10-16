/**
 * Copyright (c) 2017-present, Facebook, Inc.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */

const siteConfig = {
  title: 'PHYRE',
  tagline: 'A Benchmark For Physical Reasoning',
  url: 'https://phyre.ai',
  baseUrl: '/',
  projectName: 'PHYRE.ai',
  organizationName: 'facebook',
  favicon: 'img/favicon.ico',
  presets: [
    [
      '@docusaurus/preset-classic',
      {
        docs: {
          path: '../docs',
          sidebarPath: require.resolve('./sidebars.json'),
          editUrl:
            'https://github.com/facebookresearch/phyre',
          showLastUpdateAuthor: true,
          showLastUpdateTime: true,
        },
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
      },
    ],
  ],
  themeConfig: {
    image: 'img/phyre_logo.jpg',
    navbar: {
      title: 'Phyre.io',
      logo: {
        alt: 'Phyre.io Logo',
        src: 'img/phyre_logo.jpg',
      },
      links: [
        { href: 'https://player.phyre.ai/', label: 'Demo', position: 'right' },
        {
          href: 'https://github.com/facebookresearch/phyre',
          label: 'GitHub',
          position: 'right',
        },
        {
          href: 'https://arxiv.org/abs/1908.05656',
          label: 'Paper',
          position: 'right',
        },
        {
          href: 'https://phyre.ai/docs/index.html',
          label: 'API',
          position: 'right',
        },

      ],
    },
    footer: {
      style: 'dark',
      logo: {
        alt: 'Facebook Open Source Logo',
        src: 'img/oss_logo.png',
      },
      copyright: `Copyright © ${new Date().getFullYear()} Facebook, Inc.`,
    },
  },
};

module.exports = siteConfig;
