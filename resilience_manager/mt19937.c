/* 
   A C-program for MT19937, with initialization improved 2002/1/26.
   Coded by Takuji Nishimura and Makoto Matsumoto.

   Before using, initialize the state by using init_genrand(seed)  
   or init_by_array(init_key, key_length).

   Copyright (C) 1997 - 2002, Makoto Matsumoto and Takuji Nishimura,
   All rights reserved.                          

   Redistribution and use in source and binary forms, with or without
   modification, are permitted provided that the following conditions
   are met:

     1. Redistributions of source code must retain the above copyright
        notice, this list of conditions and the following disclaimer.

     2. Redistributions in binary form must reproduce the above copyright
        notice, this list of conditions and the following disclaimer in the
        documentation and/or other materials provided with the distribution.

     3. The names of its contributors may not be used to endorse or promote 
        products derived from this software without specific prior written 
        permission.

   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
   "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
   LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
   A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR
   CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
   EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
   PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
   PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
   LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
   NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
   SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


   Any feedback is very welcome.
   http://www.math.sci.hiroshima-u.ac.jp/~m-mat/MT/emt.html
   email: m-mat @ math.sci.hiroshima-u.ac.jp (remove space)
*/

#define MATRIX_A 0x9908b0dfUL   /* constant vector a */
#define UPPER_MASK 0x80000000UL /* most significant w-r bits */
#define LOWER_MASK 0x7fffffffUL /* least significant r bits */

#include <linux/types.h>
#include "mt19937.h"

void init_genrand(MTRand* rand, uint32_t seed) {
  rand->mt[0]= seed & 0xffffffffUL;
  for (rand->mti=1; rand->mti<MT19937_N; rand->mti++) {
    rand->mt[rand->mti] = 
    (1812433253UL * (rand->mt[rand->mti-1] ^ (rand->mt[rand->mti-1] >> 30)) + rand->mti); 
      /* See Knuth TAOCP Vol2. 3rd Ed. P.106 for multiplier. */
      /* In the previous versions, MSBs of the seed affect   */
      /* only MSBs of the array mt[].                        */
      /* 2002/01/09 modified by Makoto Matsumoto             */
      rand->mt[rand->mti] &= 0xffffffffUL;
      /* for >32 bit machines */
  }    
}

/**
 * Generates a pseudo-randomly generated long.
 */
uint32_t genrand_uint32(MTRand* rand) {
  uint32_t y;
  static uint32_t mag01[2]={0x0UL, MATRIX_A};
  /* mag01[x] = x * MATRIX_A  for x=0,1 */

  if (rand->mti >= MT19937_N) { /* generate N words at one time */
      int kk;

      if (rand->mti == MT19937_N+1)   /* if init_genrand() has not been called, */
          init_genrand(rand, 5489UL); /* a default initial seed is used */

      for (kk=0;kk<MT19937_N-MT19937_M;kk++) {
          y = (rand->mt[kk]&UPPER_MASK)|(rand->mt[kk+1]&LOWER_MASK);
          rand->mt[kk] = rand->mt[kk+MT19937_M] ^ (y >> 1) ^ mag01[y & 0x1UL];
      }
      for (;kk<MT19937_N-1;kk++) {
          y = (rand->mt[kk]&UPPER_MASK)|(rand->mt[kk+1]&LOWER_MASK);
          rand->mt[kk] = rand->mt[kk+(MT19937_M-MT19937_N)] ^ (y >> 1) ^ mag01[y & 0x1UL];
      }
      y = (rand->mt[MT19937_N-1]&UPPER_MASK)|(rand->mt[0]&LOWER_MASK);
      rand->mt[MT19937_N-1] = rand->mt[MT19937_M-1] ^ (y >> 1) ^ mag01[y & 0x1UL];

      rand->mti = 0;
  }

  y = rand->mt[rand->mti++];

  /* Tempering */
  y ^= (y >> 11);
  y ^= (y << 7) & 0x9d2c5680UL;
  y ^= (y << 15) & 0xefc60000UL;
  y ^= (y >> 18);

  return y;
}