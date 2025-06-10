// tailwind.config.js
const plugin = require('tailwindcss/plugin');

module.exports = {
  content: [
    '../templates/**/*.html',
    '../timesheet/templates/timesheet/**/*.html',
    './src/**/*.{js,ts,scss}',
  ],

  plugins: [
    plugin(({ addVariant }) => {
      addVariant('dark', '&:where([data-theme=dark], [data-theme=dark] *)');
    }),
  ],
};
