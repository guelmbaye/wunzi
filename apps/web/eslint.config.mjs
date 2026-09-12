import next from 'eslint-config-next';

export default [
  ...next,
  {
    rules: {
      // A missing key on a claim list is a correctness bug in a case file.
      'react/jsx-key': 'error',
    },
  },
];
